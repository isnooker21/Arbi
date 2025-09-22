"""
ระบบ Machine Learning สำหรับปรับปรุงการเทรด

ไฟล์นี้ทำหน้าที่:
- เก็บข้อมูลผลการเทรดและประสิทธิภาพของกฎเกณฑ์
- วิเคราะห์รูปแบบการเทรดที่ประสบความสำเร็จ
- ฝึกโมเดล AI เพื่อทำนายโอกาส Arbitrage
- ปรับปรุงพารามิเตอร์ของกฎเกณฑ์ให้เหมาะสม
- เรียนรู้จากข้อมูลตลาดและพฤติกรรมราคา

ฟีเจอร์หลัก:
- Pattern Recognition: หารูปแบบการเทรดที่ทำกำไร
- Predictive Modeling: ทำนายโอกาส Arbitrage
- Rule Optimization: ปรับปรุงกฎเกณฑ์ให้ดีขึ้น
- Performance Tracking: ติดตามผลการทำงาน
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple
import json
import sqlite3
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib
import os

class LearningModule:
    def __init__(self, db_path: str = "data/learning.db"):
        self.logger = logging.getLogger(__name__)
        self.db_path = db_path
        self.performance_data = []
        self.market_patterns = {}
        self.models = {}
        self.scaler = StandardScaler()
        
        # Initialize database
        self._init_database()
        
    def _init_database(self):
        """Initialize SQLite database for learning data"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rule_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_id TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    success BOOLEAN NOT NULL,
                    profit_loss REAL NOT NULL,
                    market_conditions TEXT,
                    confidence REAL,
                    context TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_type TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    features TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    confidence REAL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    triangle TEXT NOT NULL,
                    arbitrage_percent REAL NOT NULL,
                    market_conditions TEXT,
                    executed BOOLEAN NOT NULL,
                    profit_loss REAL,
                    confidence REAL
                )
            ''')
            
            conn.commit()
            conn.close()
            
            self.logger.info("Learning database initialized")
            
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
    
    def record_rule_performance(self, rule_id: str, success: bool, profit_loss: float, 
                              market_conditions: Dict = None, confidence: float = None, 
                              context: Dict = None):
        """Record rule performance for learning"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO rule_performance 
                (rule_id, timestamp, success, profit_loss, market_conditions, confidence, context)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                rule_id,
                datetime.now(),
                success,
                profit_loss,
                json.dumps(market_conditions) if market_conditions else None,
                confidence,
                json.dumps(context) if context else None
            ))
            
            conn.commit()
            conn.close()
            
            # Also store in memory for quick access
            self.performance_data.append({
                'rule_id': rule_id,
                'timestamp': datetime.now(),
                'success': success,
                'profit_loss': profit_loss,
                'market_conditions': market_conditions,
                'confidence': confidence,
                'context': context
            })
            
        except Exception as e:
            self.logger.error(f"Error recording rule performance: {e}")
    
    def record_arbitrage_opportunity(self, triangle: Tuple[str, str, str], 
                                   arbitrage_percent: float, market_conditions: Dict = None,
                                   executed: bool = False, profit_loss: float = None,
                                   confidence: float = None):
        """Record arbitrage opportunity for pattern learning"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO arbitrage_opportunities 
                (timestamp, triangle, arbitrage_percent, market_conditions, executed, profit_loss, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now(),
                json.dumps(triangle),
                arbitrage_percent,
                json.dumps(market_conditions) if market_conditions else None,
                executed,
                profit_loss,
                confidence
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error recording arbitrage opportunity: {e}")
    
    def analyze_rule_performance(self, rule_id: str = None, days: int = 30) -> Dict:
        """Analyze performance of specific rule or all rules"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Build query
            if rule_id:
                query = '''
                    SELECT * FROM rule_performance 
                    WHERE rule_id = ? AND timestamp >= ?
                    ORDER BY timestamp DESC
                '''
                params = (rule_id, datetime.now() - timedelta(days=days))
            else:
                query = '''
                    SELECT * FROM rule_performance 
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                '''
                params = (datetime.now() - timedelta(days=days),)
            
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            if df.empty:
                return {'error': 'No data found'}
            
            # Calculate performance metrics
            total_trades = len(df)
            successful_trades = len(df[df['success'] == True])
            win_rate = (successful_trades / total_trades) * 100 if total_trades > 0 else 0
            
            total_pnl = df['profit_loss'].sum()
            avg_pnl = df['profit_loss'].mean()
            
            # Calculate Sharpe ratio (simplified)
            returns = df['profit_loss'].values
            sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
            
            # Calculate maximum drawdown
            cumulative_pnl = np.cumsum(returns)
            running_max = np.maximum.accumulate(cumulative_pnl)
            drawdown = running_max - cumulative_pnl
            max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0
            
            return {
                'rule_id': rule_id,
                'total_trades': total_trades,
                'successful_trades': successful_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'average_pnl': avg_pnl,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'analysis_period_days': days
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing rule performance: {e}")
            return {'error': str(e)}
    
    def identify_market_patterns(self, days: int = 7) -> Dict:
        """Identify recurring market patterns"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Get recent arbitrage opportunities
            query = '''
                SELECT * FROM arbitrage_opportunities 
                WHERE timestamp >= ? AND executed = 1
                ORDER BY timestamp DESC
            '''
            df = pd.read_sql_query(query, conn, params=(datetime.now() - timedelta(days=days),))
            conn.close()
            
            if df.empty:
                return {'patterns': [], 'message': 'No executed opportunities found'}
            
            # Extract features from market conditions
            features = []
            outcomes = []
            
            for _, row in df.iterrows():
                market_conditions = json.loads(row['market_conditions']) if row['market_conditions'] else {}
                
                # Extract numerical features
                feature_vector = []
                feature_vector.append(row['arbitrage_percent'])
                feature_vector.append(market_conditions.get('volatility', 0))
                feature_vector.append(market_conditions.get('spread', 0))
                feature_vector.append(market_conditions.get('volume', 0))
                
                # Add time-based features
                timestamp = pd.to_datetime(row['timestamp'])
                feature_vector.append(timestamp.hour)
                feature_vector.append(timestamp.dayofweek)
                
                features.append(feature_vector)
                outcomes.append(1 if row['profit_loss'] > 0 else 0)
            
            if len(features) < 10:
                return {'patterns': [], 'message': 'Insufficient data for pattern analysis'}
            
            # Use K-means clustering to identify patterns
            features_array = np.array(features)
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features_array)
            
            # Find optimal number of clusters
            n_clusters = min(5, len(features) // 3)
            if n_clusters < 2:
                n_clusters = 2
            
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            cluster_labels = kmeans.fit_predict(features_scaled)
            
            # Analyze each cluster
            patterns = []
            for cluster_id in range(n_clusters):
                cluster_mask = cluster_labels == cluster_id
                cluster_outcomes = np.array(outcomes)[cluster_mask]
                cluster_features = features_array[cluster_mask]
                
                if len(cluster_outcomes) == 0:
                    continue
                
                success_rate = np.mean(cluster_outcomes)
                avg_arbitrage = np.mean(cluster_features[:, 0])
                avg_volatility = np.mean(cluster_features[:, 1])
                
                pattern = {
                    'cluster_id': cluster_id,
                    'success_rate': success_rate,
                    'avg_arbitrage_percent': avg_arbitrage,
                    'avg_volatility': avg_volatility,
                    'sample_size': len(cluster_outcomes),
                    'characteristics': {
                        'high_volatility': avg_volatility > np.mean(features_array[:, 1]),
                        'high_arbitrage': avg_arbitrage > np.mean(features_array[:, 0]),
                        'profitable': success_rate > 0.6
                    }
                }
                
                patterns.append(pattern)
            
            return {
                'patterns': patterns,
                'total_samples': len(features),
                'analysis_period_days': days
            }
            
        except Exception as e:
            self.logger.error(f"Error identifying market patterns: {e}")
            return {'error': str(e)}
    
    def train_arbitrage_classifier(self, days: int = 30) -> Dict:
        """Train a classifier to predict arbitrage success"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Get training data
            query = '''
                SELECT * FROM arbitrage_opportunities 
                WHERE timestamp >= ? AND executed = 1 AND profit_loss IS NOT NULL
                ORDER BY timestamp DESC
            '''
            df = pd.read_sql_query(query, conn, params=(datetime.now() - timedelta(days=days),))
            conn.close()
            
            if len(df) < 20:
                return {'error': 'Insufficient data for training (need at least 20 samples)'}
            
            # Prepare features
            features = []
            labels = []
            
            for _, row in df.iterrows():
                market_conditions = json.loads(row['market_conditions']) if row['market_conditions'] else {}
                
                feature_vector = [
                    row['arbitrage_percent'],
                    market_conditions.get('volatility', 0),
                    market_conditions.get('spread', 0),
                    market_conditions.get('volume', 0),
                    market_conditions.get('trend_strength', 0),
                    market_conditions.get('correlation_strength', 0)
                ]
                
                # Add time features
                timestamp = pd.to_datetime(row['timestamp'])
                feature_vector.extend([
                    timestamp.hour,
                    timestamp.dayofweek,
                    timestamp.month
                ])
                
                features.append(feature_vector)
                labels.append(1 if row['profit_loss'] > 0 else 0)
            
            # Convert to numpy arrays
            X = np.array(features)
            y = np.array(labels)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train Random Forest classifier
            rf = RandomForestClassifier(n_estimators=100, random_state=42)
            rf.fit(X_train_scaled, y_train)
            
            # Evaluate model
            train_score = rf.score(X_train_scaled, y_train)
            test_score = rf.score(X_test_scaled, y_test)
            
            # Feature importance
            feature_names = [
                'arbitrage_percent', 'volatility', 'spread', 'volume',
                'trend_strength', 'correlation_strength', 'hour', 'dayofweek', 'month'
            ]
            feature_importance = dict(zip(feature_names, rf.feature_importances_))
            
            # Save model
            model_path = f"models/arbitrage_classifier_{datetime.now().strftime('%Y%m%d')}.joblib"
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            joblib.dump((rf, scaler), model_path)
            
            self.models['arbitrage_classifier'] = (rf, scaler)
            
            return {
                'model_trained': True,
                'train_accuracy': train_score,
                'test_accuracy': test_score,
                'feature_importance': feature_importance,
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'model_path': model_path
            }
            
        except Exception as e:
            self.logger.error(f"Error training arbitrage classifier: {e}")
            return {'error': str(e)}
    
    def predict_arbitrage_success(self, features: Dict) -> Dict:
        """Predict success probability for arbitrage opportunity"""
        try:
            if 'arbitrage_classifier' not in self.models:
                return {'error': 'Model not trained yet'}
            
            rf, scaler = self.models['arbitrage_classifier']
            
            # Prepare feature vector
            feature_vector = [
                features.get('arbitrage_percent', 0),
                features.get('volatility', 0),
                features.get('spread', 0),
                features.get('volume', 0),
                features.get('trend_strength', 0),
                features.get('correlation_strength', 0),
                features.get('hour', datetime.now().hour),
                features.get('dayofweek', datetime.now().weekday()),
                features.get('month', datetime.now().month)
            ]
            
            # Scale features
            X = np.array(feature_vector).reshape(1, -1)
            X_scaled = scaler.transform(X)
            
            # Predict
            success_probability = rf.predict_proba(X_scaled)[0][1]
            prediction = rf.predict(X_scaled)[0]
            
            return {
                'success_probability': success_probability,
                'prediction': bool(prediction),
                'confidence': success_probability if prediction else 1 - success_probability
            }
            
        except Exception as e:
            self.logger.error(f"Error predicting arbitrage success: {e}")
            return {'error': str(e)}
    
    def optimize_rule_parameters(self, rule_id: str, days: int = 30) -> Dict:
        """Optimize parameters for a specific rule"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Get rule performance data
            query = '''
                SELECT * FROM rule_performance 
                WHERE rule_id = ? AND timestamp >= ?
                ORDER BY timestamp DESC
            '''
            df = pd.read_sql_query(query, conn, params=(rule_id, datetime.now() - timedelta(days=days)))
            conn.close()
            
            if len(df) < 10:
                return {'error': 'Insufficient data for optimization'}
            
            # Analyze performance by different conditions
            # This is a simplified optimization - in practice, you'd use more sophisticated methods
            
            # Group by confidence levels
            confidence_groups = df.groupby(pd.cut(df['confidence'], bins=5))
            
            best_confidence_range = None
            best_performance = -float('inf')
            
            for name, group in confidence_groups:
                if len(group) < 3:  # Skip groups with too few samples
                    continue
                
                success_rate = group['success'].mean()
                avg_pnl = group['profit_loss'].mean()
                
                # Simple performance metric: success_rate * avg_pnl
                performance = success_rate * avg_pnl
                
                if performance > best_performance:
                    best_performance = performance
                    best_confidence_range = name
            
            # Analyze market conditions
            market_analysis = {}
            for _, row in df.iterrows():
                if row['market_conditions']:
                    conditions = json.loads(row['market_conditions'])
                    for key, value in conditions.items():
                        if key not in market_analysis:
                            market_analysis[key] = []
                        market_analysis[key].append((value, row['success'], row['profit_loss']))
            
            # Find optimal ranges for each market condition
            optimal_ranges = {}
            for condition, values in market_analysis.items():
                if len(values) < 5:
                    continue
                
                # Sort by value and analyze performance
                values.sort(key=lambda x: x[0])
                
                # Find range with best performance
                best_range = None
                best_perf = -float('inf')
                
                for i in range(len(values) - 4):
                    subset = values[i:i+5]
                    success_rate = sum(1 for _, success, _ in subset if success) / len(subset)
                    avg_pnl = sum(pnl for _, _, pnl in subset) / len(subset)
                    performance = success_rate * avg_pnl
                    
                    if performance > best_perf:
                        best_perf = performance
                        best_range = (subset[0][0], subset[-1][0])
                
                if best_range:
                    optimal_ranges[condition] = best_range
            
            return {
                'rule_id': rule_id,
                'best_confidence_range': str(best_confidence_range) if best_confidence_range else None,
                'optimal_market_conditions': optimal_ranges,
                'total_samples': len(df),
                'optimization_period_days': days
            }
            
        except Exception as e:
            self.logger.error(f"Error optimizing rule parameters: {e}")
            return {'error': str(e)}
    
    def get_learning_summary(self) -> Dict:
        """Get summary of learning module status"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Get counts
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM rule_performance")
            rule_performance_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM arbitrage_opportunities")
            arbitrage_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM market_patterns")
            pattern_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'rule_performance_records': rule_performance_count,
                'arbitrage_opportunities': arbitrage_count,
                'market_patterns': pattern_count,
                'trained_models': list(self.models.keys()),
                'database_path': self.db_path
            }
            
        except Exception as e:
            self.logger.error(f"Error getting learning summary: {e}")
            return {'error': str(e)}
