# database/setup.py
# Run this ONCE to create all tables and views in MySQL.
# Usage: python database/setup.py

import mysql.connector
from db_connection import DB_CONFIG

SCHEMA_SQL = """
CREATE DATABASE IF NOT EXISTS ekitchen;
USE ekitchen;

CREATE TABLE IF NOT EXISTS units (
    id INT AUTO_INCREMENT PRIMARY KEY,
    unit_name VARCHAR(20) NOT NULL UNIQUE,
    base_unit VARCHAR(10) NOT NULL,
    to_base_factor DECIMAL(10,4) NOT NULL
);

INSERT IGNORE INTO units (unit_name, base_unit, to_base_factor) VALUES
    ('g',    'g',   1.0),
    ('kg',   'g',   1000.0),
    ('mg',   'g',   0.001),
    ('ml',   'ml',  1.0),
    ('l',    'ml',  1000.0),
    ('tsp',  'ml',  5.0),
    ('tbsp', 'ml',  15.0),
    ('cup',  'ml',  240.0),
    ('pcs',  'pcs', 1.0);

CREATE TABLE IF NOT EXISTS pantry_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(50),
    current_qty DECIMAL(10,2) NOT NULL DEFAULT 0,
    unit VARCHAR(20),
    shelf_life_days INT,
    purchase_date DATE,
    expiry_date DATE,
    cost_per_unit DECIMAL(10,2),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (unit) REFERENCES units(unit_name)
);

CREATE TABLE IF NOT EXISTS grocery_purchases (
    id INT AUTO_INCREMENT PRIMARY KEY,
    item_id INT,
    quantity_bought DECIMAL(10,2) NOT NULL,
    unit VARCHAR(20),
    cost DECIMAL(10,2),
    purchase_date DATE,
    shop_name VARCHAR(100),
    notes TEXT,
    FOREIGN KEY (item_id) REFERENCES pantry_items(id),
    FOREIGN KEY (unit) REFERENCES units(unit_name)
);

CREATE TABLE IF NOT EXISTS recipes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    cuisine VARCHAR(50),
    servings INT DEFAULT 2,
    prep_time_mins INT,
    cook_time_mins INT,
    instructions TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    recipe_id INT,
    ingredient_name VARCHAR(100) NOT NULL,
    quantity_required DECIMAL(10,2) NOT NULL,
    unit VARCHAR(20),
    is_optional TINYINT(1) DEFAULT 0,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    FOREIGN KEY (unit) REFERENCES units(unit_name)
);

CREATE TABLE IF NOT EXISTS cook_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    recipe_id INT,
    recipe_name VARCHAR(150),
    servings_cooked INT DEFAULT 1,
    cooked_on DATE,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id)
);

CREATE TABLE IF NOT EXISTS cook_log_ingredients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cook_log_id INT,
    ingredient_name VARCHAR(100) NOT NULL,
    quantity_used DECIMAL(10,2) NOT NULL,
    unit VARCHAR(20),
    FOREIGN KEY (cook_log_id) REFERENCES cook_logs(id) ON DELETE CASCADE,
    FOREIGN KEY (unit) REFERENCES units(unit_name)
);

CREATE TABLE IF NOT EXISTS waste_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    item_id INT,
    item_name VARCHAR(100) NOT NULL,
    quantity_wasted DECIMAL(10,2) NOT NULL,
    unit VARCHAR(20),
    reason VARCHAR(100),
    wasted_on DATE,
    estimated_cost DECIMAL(10,2),
    FOREIGN KEY (unit) REFERENCES units(unit_name)
);
"""

VIEWS_SQL = [
    """
    CREATE OR REPLACE VIEW v_pantry_status AS
    SELECT
        p.id, p.name, p.category, p.current_qty, p.unit,
        p.expiry_date, p.cost_per_unit,
        CASE
            WHEN p.expiry_date IS NULL THEN 'unknown'
            WHEN p.expiry_date < CURDATE() THEN 'expired'
            WHEN p.expiry_date <= DATE_ADD(CURDATE(), INTERVAL 3 DAY) THEN 'expiring_soon'
            ELSE 'ok'
        END AS expiry_status,
        DATEDIFF(p.expiry_date, CURDATE()) AS days_until_expiry
    FROM pantry_items p
    WHERE p.current_qty > 0
    ORDER BY p.expiry_date ASC
    """,
    """
    CREATE OR REPLACE VIEW v_monthly_summary AS
    SELECT
        DATE_FORMAT(purchase_date, '%Y-%m') AS month,
        SUM(cost) AS total_spent,
        COUNT(DISTINCT id) AS purchase_trips
    FROM grocery_purchases
    GROUP BY DATE_FORMAT(purchase_date, '%Y-%m')
    ORDER BY month DESC
    """,
    """
    CREATE OR REPLACE VIEW v_waste_summary AS
    SELECT
        item_name,
        SUM(quantity_wasted) AS total_wasted,
        unit,
        SUM(estimated_cost) AS total_cost_wasted,
        COUNT(*) AS waste_events
    FROM waste_log
    GROUP BY item_name, unit
    ORDER BY total_cost_wasted DESC
    """,
    """
    CREATE OR REPLACE VIEW v_ingredient_usage AS
    SELECT
        cli.ingredient_name,
        SUM(cli.quantity_used) AS total_used,
        cli.unit,
        COUNT(*) AS times_cooked
    FROM cook_log_ingredients cli
    GROUP BY cli.ingredient_name, cli.unit
    ORDER BY total_used DESC
    """
]


def run_setup():
    # Connect without specifying database first
    config = {k: v for k, v in DB_CONFIG.items() if k != "database"}
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()

    print("Creating database and tables...")
    for statement in SCHEMA_SQL.strip().split(";"):
        s = statement.strip()
        if s:
            cursor.execute(s)
            conn.commit()

    print("Creating views...")
    for view_sql in VIEWS_SQL:
        cursor.execute(f"USE ekitchen")
        cursor.execute(view_sql)
        conn.commit()

    cursor.close()
    conn.close()
    print("\n✅ Setup complete! All tables and views created in 'ekitchen' database.")
    print("Now run:  streamlit run app.py")


if __name__ == "__main__":
    run_setup()
