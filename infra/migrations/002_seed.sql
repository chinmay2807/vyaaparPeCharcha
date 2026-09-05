BEGIN;

INSERT INTO merchants (id, name, timezone, default_language, invoice_settings) VALUES
  ('mer_demo', 'Jai Hind Distributors', 'Asia/Kolkata', 'hi-IN', '{"prefix":"VL","address":"Sadar Bazaar, Delhi"}');

INSERT INTO users (id, merchant_id, role, identity) VALUES
  ('usr_demo', 'mer_demo', 'owner', 'demo@local');

INSERT INTO customers (id, merchant_id, canonical_name, aliases, phone, address, credit_limit_minor) VALUES
  ('cus_ramesh', 'mer_demo', 'Ramesh Kirana', ARRAY['Ramesh','Ramesh ji','रमेश'], '***0001', 'Lajpat Nagar, Delhi', 5000000),
  ('cus_sharma', 'mer_demo', 'Sharma Stores', ARRAY['Sharma','Sharma Store','शर्मा स्टोर्स'], '***0002', 'Karol Bagh, Delhi', 3000000),
  ('cus_gupta', 'mer_demo', 'Gupta General Store', ARRAY['Gupta','Gupta ji','Gupta Stores'], '***0003', 'Paharganj, Delhi', 4000000),
  ('cus_aman', 'mer_demo', 'Aman Mart', ARRAY['Aman','Aman Market'], '***0004', 'Patel Nagar, Delhi', 2500000),
  ('cus_khan', 'mer_demo', 'Khan Traders', ARRAY['Khan','Khan saab'], '***0005', 'Daryaganj, Delhi', 3500000);

INSERT INTO skus (id, merchant_id, canonical_label, aliases, base_unit, units_per_case, selling_price_minor, stock) VALUES
  ('sku_sprite_250','mer_demo','Sprite 250ml × 24',ARRAY['Sprite peti','Sprite crate','Sprite case','स्प्राइट पेटी'],'case',24,96000,80),
  ('sku_coke_250','mer_demo','Coca-Cola 250ml × 24',ARRAY['Coke peti','Coke crate','Coke case','कोक पेटी'],'case',24,99000,72),
  ('sku_limca_250','mer_demo','Limca 250ml × 24',ARRAY['Limca peti','Limca case','लिम्का पेटी'],'case',24,96000,65),
  ('sku_fanta_250','mer_demo','Fanta 250ml × 24',ARRAY['Fanta peti','Fanta case','फैंटा पेटी'],'case',24,96000,54),
  ('sku_thumsup_250','mer_demo','Thums Up 250ml × 24',ARRAY['Thums Up peti','Thumbs up crate','थम्स अप पेटी'],'case',24,99000,60),
  ('sku_maaza_200','mer_demo','Maaza 200ml × 24',ARRAY['Maaza carton','Maza peti','माज़ा पेटी'],'case',24,84000,48),
  ('sku_kinley_1l','mer_demo','Kinley Water 1L × 12',ARRAY['Kinley case','water bottle case','पानी पेटी'],'case',12,24000,100),
  ('sku_bisleri_1l','mer_demo','Bisleri Water 1L × 12',ARRAY['Bisleri case','Bisleri peti'],'case',12,26000,90),
  ('sku_soda_750','mer_demo','Kinley Soda 750ml × 12',ARRAY['soda case','soda peti'],'case',12,30000,45),
  ('sku_redbull_250','mer_demo','Red Bull 250ml × 24',ARRAY['Red Bull case','energy drink peti'],'case',24,300000,18),
  ('sku_real_mango','mer_demo','Real Mango 1L × 12',ARRAY['mango juice carton','Real juice case'],'case',12,132000,30),
  ('sku_tropicana_orange','mer_demo','Tropicana Orange 1L × 12',ARRAY['orange juice carton','Tropicana case'],'case',12,144000,24),
  ('sku_amul_milk','mer_demo','Amul Taaza 1L × 12',ARRAY['milk carton','Amul milk case'],'case',12,72000,36),
  ('sku_tata_salt','mer_demo','Tata Salt 1kg × 25',ARRAY['salt bora','Tata namak carton'],'case',25,67500,40),
  ('sku_sugar_1kg','mer_demo','Sugar 1kg × 20',ARRAY['sugar bag','cheeni carton'],'case',20,96000,42),
  ('sku_aashirvaad_5kg','mer_demo','Aashirvaad Atta 5kg × 4',ARRAY['atta carton','Aashirvaad case'],'case',4,112000,30),
  ('sku_fortune_oil','mer_demo','Fortune Oil 1L × 12',ARRAY['Fortune carton','oil case'],'case',12,156000,38),
  ('sku_tata_tea','mer_demo','Tata Tea 500g × 12',ARRAY['chai patti carton','Tata tea case'],'case',12,174000,22),
  ('sku_parleg','mer_demo','Parle-G 800g × 12',ARRAY['Parle G carton','biscuit case'],'case',12,90000,50),
  ('sku_goodday','mer_demo','Good Day 200g × 24',ARRAY['Good Day carton','Goodday case'],'case',24,72000,46),
  ('sku_maggi','mer_demo','Maggi 70g × 96',ARRAY['Maggi carton','noodle case'],'case',96,134400,34),
  ('sku_lays_blue','mer_demo','Lays Blue 50g × 48',ARRAY['blue Lays carton','chips case'],'case',48,96000,44),
  ('sku_kurkure','mer_demo','Kurkure 55g × 48',ARRAY['Kurkure carton','namkeen case'],'case',48,96000,40),
  ('sku_surfexcel','mer_demo','Surf Excel 1kg × 12',ARRAY['Surf carton','detergent case'],'case',12,180000,28),
  ('sku_rin','mer_demo','Rin Bar 250g × 48',ARRAY['Rin carton','soap case'],'case',48,120000,32),
  ('sku_lifebuoy','mer_demo','Lifebuoy Soap 125g × 48',ARRAY['Lifebuoy carton','sabun case'],'case',48,144000,36),
  ('sku_clinicplus','mer_demo','Clinic Plus Sachet × 192',ARRAY['shampoo pouch carton','Clinic pouch'],'case',192,96000,25),
  ('sku_colgate','mer_demo','Colgate 200g × 24',ARRAY['Colgate carton','toothpaste case'],'case',24,216000,20),
  ('sku_detol','mer_demo','Dettol 200ml × 48',ARRAY['Dettol carton','antiseptic case'],'case',48,336000,16),
  ('sku_eveready','mer_demo','Eveready AA × 60',ARRAY['battery carton','cell case'],'case',60,150000,26);

INSERT INTO ledger_entries (id, merchant_id, customer_id, source_type, source_id, amount_minor, direction) VALUES
  ('led_open_ramesh','mer_demo','cus_ramesh','opening_balance','open_ramesh',1250000,'debit');

COMMIT;
