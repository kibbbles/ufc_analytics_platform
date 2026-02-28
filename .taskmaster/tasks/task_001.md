# Task ID: 1

**Title:** Database Schema Setup

**Status:** done

**Dependencies:** None

**Priority:** high

**Description:** Design and implement the PostgreSQL database schema with core entities (Fighter, Fight, FightStats, Event) as specified in the PRD.

**Details:**

Create a Supabase PostgreSQL database with the following tables:

1. fighters table with columns:
   - id (SERIAL, primary key)
   - name (varchar)
   - height_cm (float)
   - weight_lbs (float)
   - reach_inches (float)
   - stance (varchar)
   - birth_date (date)
   - wins (integer)
   - losses (integer)
   - draws (integer)
   - no_contests (integer)

2. events table with columns:
   - id (SERIAL, primary key)
   - name (varchar)
   - date (timestamp)
   - city (varchar)
   - country (varchar)
   - venue (varchar)

3. fights table with columns:
   - id (SERIAL, primary key)
   - event_id (integer, foreign key)
   - fighter_a_id (integer, foreign key)
   - fighter_b_id (integer, foreign key)
   - winner_id (integer, foreign key, nullable)
   - method (varchar)
   - round (integer)
   - time (time)
   - weight_class (varchar)
   - is_title_fight (boolean)

4. fight_stats table with columns:
   - id (SERIAL, primary key)
   - fight_id (integer, foreign key)
   - fighter_id (integer, foreign key)
   - total_strikes (integer)
   - total_takedowns (integer)
   - total_control_time (interval)

5. round_stats table with columns:
   - id (SERIAL, primary key)
   - fight_stats_id (integer, foreign key)
   - round_number (integer)
   - strikes_landed (integer)
   - strikes_attempted (integer)
   - takedowns (integer)
   - control_time (interval)

Implement using SQLAlchemy 2.0 ORM with appropriate relationships and indexes. Create Alembic migrations for version control of the schema.

**Test Strategy:**

1. Write unit tests for SQLAlchemy models to verify relationships and constraints
2. Create test fixtures with sample data
3. Test database migrations (up and down)
4. Verify foreign key constraints and cascading deletes
5. Benchmark query performance with test data
6. Validate SERIAL primary key generation and constraints
