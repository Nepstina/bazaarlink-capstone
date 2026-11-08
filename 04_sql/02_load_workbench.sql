-- =====================================================================
-- BazaarLink capstone | 02_load.sql
-- Loads the CLEANED CSVs (02_data/cleaned/, made by clean_data.py).
--
-- C:/Users/AWAN.Admin/Desktop/E-commerce capstone project/Script/02_data/cleaned is replaced by run_sql.py with the full path to 02_data/cleaned.
-- To run by hand in MySQL Workbench: replace C:/Users/AWAN.Admin/Desktop/E-commerce capstone project/Script/02_data/cleaned with that path using
-- forward slashes (e.g. C:/projects/bazaarlink-capstone/02_data/cleaned),
-- and enable local_infile (SET GLOBAL local_infile = 1; plus
-- OPT_LOCAL_INFILE=1 in the Workbench connection's Advanced settings).
--
-- Why this loader: review comments contain commas and quotes, so fields are
-- read with OPTIONALLY ENCLOSED BY '"'. Blank values become NULL with NULLIF.
-- Extra derived columns at the end of each cleaned CSV are ignored.
-- Load order follows the foreign keys: parents first.
-- =====================================================================
USE bazaarlink;

LOAD DATA LOCAL INFILE 'C:/Users/AWAN.Admin/Desktop/E-commerce capstone project/Script/02_data/cleaned/customers.csv'
INTO TABLE customers CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n' IGNORE 1 LINES
(customer_id, customer_unique_id, @zip, customer_city, customer_state)
SET customer_zip_code_prefix = LPAD(@zip, 5, '0');

LOAD DATA LOCAL INFILE 'C:/Users/AWAN.Admin/Desktop/E-commerce capstone project/Script/02_data/cleaned/sellers.csv'
INTO TABLE sellers CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n' IGNORE 1 LINES
(seller_id, @zip, seller_city, seller_state)
SET seller_zip_code_prefix = LPAD(@zip, 5, '0');

LOAD DATA LOCAL INFILE 'C:/Users/AWAN.Admin/Desktop/E-commerce capstone project/Script/02_data/cleaned/products.csv'
INTO TABLE products CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n' IGNORE 1 LINES
(product_id, product_category_name, @name_len, @desc_len, @photos,
 @weight, @length, @height, @width, product_category_english)
SET product_name_length        = CAST(NULLIF(@name_len, '') AS DECIMAL(8,1)),
    product_description_length = CAST(NULLIF(@desc_len, '') AS DECIMAL(8,1)),
    product_photos_qty         = CAST(NULLIF(@photos, '')   AS DECIMAL(8,1)),
    product_weight_g           = NULLIF(@weight, ''),
    product_length_cm          = NULLIF(@length, ''),
    product_height_cm          = NULLIF(@height, ''),
    product_width_cm           = NULLIF(@width, '');

LOAD DATA LOCAL INFILE 'C:/Users/AWAN.Admin/Desktop/E-commerce capstone project/Script/02_data/cleaned/orders.csv'
INTO TABLE orders CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n' IGNORE 1 LINES
(order_id, customer_id, order_status, @purchase, @approved, @carrier, @delivered, @estimated)
SET order_purchase_timestamp      = @purchase,
    order_approved_at             = NULLIF(@approved, ''),
    order_delivered_carrier_date  = NULLIF(@carrier, ''),
    order_delivered_customer_date = NULLIF(@delivered, ''),
    order_estimated_delivery_date = @estimated;

LOAD DATA LOCAL INFILE 'C:/Users/AWAN.Admin/Desktop/E-commerce capstone project/Script/02_data/cleaned/order_items.csv'
INTO TABLE order_items CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n' IGNORE 1 LINES
(order_id, order_item_id, product_id, seller_id, @limit_date, price, freight_value)
SET shipping_limit_date = NULLIF(@limit_date, '');

LOAD DATA LOCAL INFILE 'C:/Users/AWAN.Admin/Desktop/E-commerce capstone project/Script/02_data/cleaned/payments.csv'
INTO TABLE payments CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n' IGNORE 1 LINES
(order_id, payment_sequential, payment_type, payment_installments, payment_value);

LOAD DATA LOCAL INFILE 'C:/Users/AWAN.Admin/Desktop/E-commerce capstone project/Script/02_data/cleaned/reviews.csv'
INTO TABLE reviews CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n' IGNORE 1 LINES
(review_id, order_id, review_score, review_comment_title, review_comment_message,
 @created, @answered)
SET review_creation_date    = NULLIF(@created, ''),
    review_answer_timestamp = NULLIF(@answered, '');

-- Row-count check after loading (compare with 02_data/logs/row_counts.csv)
SELECT 'customers' AS table_name, COUNT(*) AS row_count FROM customers
UNION ALL SELECT 'sellers',     COUNT(*) FROM sellers
UNION ALL SELECT 'products',    COUNT(*) FROM products
UNION ALL SELECT 'orders',      COUNT(*) FROM orders
UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL SELECT 'payments',    COUNT(*) FROM payments
UNION ALL SELECT 'reviews',     COUNT(*) FROM reviews;

