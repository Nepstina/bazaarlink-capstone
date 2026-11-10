-- =====================================================================
-- BazaarLink capstone | 01_schema.sql
-- =====================================================================

DROP DATABASE IF EXISTS bazaarlink;
CREATE DATABASE bazaarlink CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE bazaarlink;

-- One row per customer_id 
CREATE TABLE customers (
    customer_id   CHAR(32)  NOT NULL,
    customer_unique_id  CHAR(32)  NOT NULL,
    customer_zip_code_prefix CHAR(5),
    customer_city VARCHAR(64),
    customer_state CHAR(2) NOT NULL,
    PRIMARY KEY (customer_id),
    INDEX idx_customers_unique (customer_unique_id),
    INDEX idx_customers_state (customer_state)
);

-- One row per seller
CREATE TABLE sellers (
    seller_id   CHAR(32)  NOT NULL,
    seller_zip_code_prefix CHAR(5),
    seller_city   VARCHAR(64),
    seller_state  CHAR(2) NOT NULL,
    PRIMARY KEY (seller_id),
    INDEX idx_sellers_state (seller_state)
);

-- One row per product 
CREATE TABLE products (
    product_id CHAR(32) NOT NULL,
    product_category_name  VARCHAR(64) NOT NULL DEFAULT 'unknown',
    product_name_length  SMALLINT,
    product_description_length SMALLINT,
    product_photos_qty  SMALLINT,
    product_weight_g   DECIMAL(10,1),
    product_length_cm  DECIMAL(8,1),
    product_height_cm    DECIMAL(8,1),
    product_width_cm   DECIMAL(8,1),
    product_category_english  VARCHAR(64) NOT NULL DEFAULT 'unknown',
    PRIMARY KEY (product_id),
    INDEX idx_products_category (product_category_english)
);

-- One row per order
CREATE TABLE orders (
    order_id  CHAR(32) NOT NULL,
    customer_id  CHAR(32)  NOT NULL,
    order_status  VARCHAR(20) NOT NULL,
    order_purchase_timestamp   DATETIME  NOT NULL,
    order_approved_at   DATETIME    NULL,
    order_delivered_carrier_date  DATETIME  NULL,
    order_delivered_customer_date DATETIME  NULL,
    order_estimated_delivery_date DATETIME   NOT NULL,
    PRIMARY KEY (order_id),
    CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
    INDEX idx_orders_status (order_status),
    INDEX idx_orders_purchase (order_purchase_timestamp)
);

-- One row per item in an order
CREATE TABLE order_items (
    order_id   CHAR(32)  NOT NULL,
    order_item_id  SMALLINT NOT NULL,
    product_id  CHAR(32)  NOT NULL,
    seller_id   CHAR(32)  NOT NULL,
    shipping_limit_date DATETIME,
    price    DECIMAL(10,2) NOT NULL,
    freight_value DECIMAL(10,2) NOT NULL,
    PRIMARY KEY (order_id, order_item_id),
    CONSTRAINT fk_items_order  FOREIGN KEY (order_id)  REFERENCES orders (order_id),
    CONSTRAINT fk_items_product FOREIGN KEY (product_id) REFERENCES products (product_id),
    CONSTRAINT fk_items_seller  FOREIGN KEY (seller_id)  REFERENCES sellers (seller_id),
    INDEX idx_items_seller (seller_id),
    INDEX idx_items_product (product_id)
);

-- One row per payment line
CREATE TABLE payments (
    order_id CHAR(32)  NOT NULL,
    payment_sequential SMALLINT  NOT NULL,
    payment_type  VARCHAR(20)  NOT NULL,
    payment_installments SMALLINT  NOT NULL,
    payment_value DECIMAL(10,2) NOT NULL,
    PRIMARY KEY (order_id, payment_sequential),
    CONSTRAINT fk_payments_order FOREIGN KEY (order_id) REFERENCES orders (order_id)
);

-- One review per order 
CREATE TABLE reviews (
    order_id CHAR(32)  NOT NULL,
    review_id  CHAR(32)  NOT NULL,
    review_score   TINYINT   NOT NULL,
    review_comment_title   VARCHAR(255),
    review_comment_message  TEXT,
    review_creation_date  DATETIME,
    review_answer_timestamp DATETIME,
    PRIMARY KEY (order_id),
    CONSTRAINT fk_reviews_order FOREIGN KEY (order_id) REFERENCES orders (order_id),
    CONSTRAINT chk_review_score CHECK (review_score BETWEEN 1 AND 5),
    INDEX idx_reviews_review_id (review_id)
);
