"""
Database integration for UFC scraper
Replaces CSV-only output with direct database storage
"""

import pandas as pd
import logging
import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add backend directory to path for imports
backend_dir = os.path.join(os.path.dirname(__file__), '..')
sys.path.append(backend_dir)

try:
    from db.models import Fighter, Event, Fight, FightStat, FighterTott, FightResults
    from db.database import get_db_engine, SessionLocal
    print("Successfully imported database models")
except ImportError as e:
    logging.error(f"Could not import database models: {e}")
    logging.info("Make sure backend database is properly set up")
    # Set to None so we can handle gracefully
    Fighter = Event = Fight = FightStat = None
    get_db_engine = SessionLocal = None

class DatabaseIntegration:
    """
    Handles saving scraped UFC data directly to PostgreSQL database
    """
    
    def __init__(self, connection_string=None):
        self.engine = None
        self.Session = None
        self.setup_database(connection_string)
    
    def setup_database(self, connection_string=None):
        """Setup database connection"""
        try:
            if connection_string:
                self.engine = create_engine(connection_string)
            else:
                # Use the existing database setup from backend
                self.engine = get_db_engine()
            
            self.Session = sessionmaker(bind=self.engine)
            logging.info("Database connection established")
            
        except Exception as e:
            logging.error(f"Failed to setup database: {e}")
            self.engine = None
            self.Session = None
    
    def test_connection(self):
        """Test database connection"""
        if not self.engine:
            return False
            
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                logging.info("Database connection test successful")
                return True
        except Exception as e:
            logging.error(f"Database connection test failed: {e}")
            return False
    
    def save_events_to_db(self, events_df):
        """
        Save events data to database
        
        Arguments:
        events_df: DataFrame with events data
        
        Returns:
        bool: True if successful
        """
        
        if self.Session is None or events_df.empty:
            return False
        
        try:
            session = self.Session()
            
            events_saved = 0
            events_updated = 0
            
            for _, row in events_df.iterrows():
                try:
                    # Check if event already exists
                    existing_event = session.query(Event).filter_by(url=row['URL']).first()
                    
                    if existing_event:
                        # Update existing event
                        existing_event.name = row['EVENT']
                        existing_event.location = row['LOCATION']
                        # Parse and update date if possible
                        try:
                            event_date = pd.to_datetime(row['DATE'], errors='coerce')
                            if pd.notna(event_date):
                                existing_event.date = event_date.date()
                        except:
                            pass
                        events_updated += 1
                    else:
                        # Create new event
                        event_date = None
                        try:
                            event_date = pd.to_datetime(row['DATE'], errors='coerce')
                            if pd.notna(event_date):
                                event_date = event_date.date()
                        except:
                            pass
                        
                        new_event = Event(
                            name=row['EVENT'],
                            date=event_date,
                            location=row['LOCATION'],
                            url=row['URL']
                        )
                        session.add(new_event)
                        events_saved += 1
                
                except Exception as e:
                    logging.error(f"Error processing event {row.get('EVENT', 'Unknown')}: {e}")
                    continue
            
            session.commit()
            session.close()
            
            logging.info(f"Events saved to database: {events_saved} new, {events_updated} updated")
            return True
            
        except Exception as e:
            logging.error(f"Error saving events to database: {e}")
            if session:
                session.rollback()
                session.close()
            return False
    
    def save_fight_stats_to_db(self, fight_stats_df):
        """
        Save detailed fight statistics to database as raw data
        
        Arguments:
        fight_stats_df: DataFrame with fight statistics
        
        Returns:
        bool: True if successful  
        """
        
        if self.Session is None or fight_stats_df.empty:
            return False
        
        try:
            # Save to fight_results table using pandas to_sql
            fight_stats_df.to_sql(
                'fight_results',
                self.engine,
                if_exists='append',
                index=False,
                method='multi'
            )
            
            logging.info(f"Saved {len(fight_stats_df)} fight stat records to database")
            return True
            
        except Exception as e:
            logging.error(f"Error saving fight stats to database: {e}")
            return False
    
    def save_all_data_to_db(self, data_dict):
        """
        Save all scraped data to database
        
        Arguments:
        data_dict: dictionary with all scraped DataFrames
        
        Returns:
        dict: results summary
        """
        
        results = {
            'events': False,
            'fight_stats': False
        }
        
        # Save events
        if 'events' in data_dict and not data_dict['events'].empty:
            results['events'] = self.save_events_to_db(data_dict['events'])
        
        # Save fight stats as raw data
        if 'fight_stats' in data_dict and not data_dict['fight_stats'].empty:
            results['fight_stats'] = self.save_fight_stats_to_db(data_dict['fight_stats'])
        
        return results

def main():
    """Test database integration"""
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    
    # Setup basic logging
    logging.basicConfig(level=logging.INFO)
    
    db_integration = DatabaseIntegration()
    
    if db_integration.test_connection():
        logging.info("Database integration test passed")
    else:
        logging.error("Database integration test failed")

if __name__ == "__main__":
    main()