# Diwali crackers billing (local Flask + PostgreSQL)

This app runs on your Windows laptop and stores products and invoices in PostgreSQL. It makes no external API or CDN requests. A phone can open the app over the same private Wi-Fi; the Wi-Fi router does not need internet access. For a no-network setup, open it on the laptop and use a USB barcode scanner or keyboard.

## One-time setup

1. Install Python 3.11+ and PostgreSQL locally. In pgAdmin, create a database named `Crackers`. The app uses host `localhost`, port `5432`, and user `postgres`; it reads the password from the `PGPASSWORD` environment variable.
2. Open PowerShell in this folder. Create a virtual environment and install packages:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. Set the PostgreSQL password for this PowerShell session, then start the app:

   ```powershell
   $securePassword = Read-Host "PostgreSQL password" -AsSecureString
   $env:PGPASSWORD = [System.Net.NetworkCredential]::new("", $securePassword).Password
   python .\app.py
   ```

   The database tables are created automatically on first start. Keep the laptop running while billing.

4. On the laptop open `http://127.0.0.1:5000`. On a phone connected to the same Wi-Fi, open `http://LAPTOP-LOCAL-IP:5000` (find the laptop IPv4 address with `ipconfig`). Windows Firewall may ask to allow Python on your **Private** network; permit only the private network if you want phone access. This serves the app on your LAN only; do not configure router port forwarding.

## Load the 2026 catalogue into pgAdmin

The CSV has 140 products. `No` is preserved as the source catalogue number; `Type` becomes the category, `Product` becomes the product/variant name, and `Price` is the single selling price. There is no wholesale price or inventory count. Quantity is entered per customer bill.

1. In pgAdmin select the `Crackers` database, open **Tools → Query Tool**, and run `reset_database_for_catalog.sql`. This deliberately drops the old app product and sales tables so their incompatible schema and sample records are cleared.
2. Right-click **Tables → products → Import/Export Data**. Choose `product_catalog_import.csv`, set **Import**, format **CSV**, enable **Header**, set encoding **UTF8**, and set the column list in this exact order: `source_no, sku, barcode, category, name, price, active`. The database `id` and `created_at` columns are generated automatically.
3. Start/restart the app. The catalogue page and billing search/dropdown will show all imported products. Barcode labels use the generated reusable barcode for each row.

## Use

- Add each product and its single price. The app assigns an internal SKU and a unique Code 128 barcode per product variant.
- Print barcode labels, verify label sizing in print preview, and apply the same label to each pack of that product type.
- Scan using a USB scanner in the barcode field, or use the phone camera button on a browser that supports the built-in `BarcodeDetector` API. Manual product selection is also available. A phone camera may require the browser to consider the page a secure context; on plain HTTP LAN addresses, support varies. The USB scanner/manual fallback works locally without that requirement.
- Set the quantity the customer is buying on the bill. The invoice and its item quantities are saved; the app does not track warehouse stock. Receipts are printable. Daily invoice totals are on Sales report.

## Backups and security

Back up the `Crackers` database regularly from pgAdmin (right-click database → Backup). Keep the backup on a separate drive. The configured PostgreSQL password is the one supplied for your local setup; set a private password if you later change it. Set `FLASK_SECRET` to a random value and keep this service on your trusted local network.

The initial installation of Python packages requires internet unless you already have the packages or use offline installers. After setup, billing runs without internet.
