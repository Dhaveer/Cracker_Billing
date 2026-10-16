# Diwali crackers billing (local Flask + PostgreSQL)

This app runs on your Windows laptop and stores products, invoices, and stock in PostgreSQL. It makes no external API or CDN requests. A phone can open the app over the same private Wi-Fi; the Wi-Fi router does not need internet access. For a no-network setup, open it on the laptop and use a USB barcode scanner or keyboard.

## One-time setup

1. Install Python 3.11+ and PostgreSQL locally. In pgAdmin, create a database named `Crackers` and use the local connection settings: host `localhost`, port `5432`, user `postgres`, password `postgres`.
2. Open PowerShell in this folder. Create a virtual environment and install packages:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. The app defaults to your `Crackers` database with those connection settings. Start it with:

   ```powershell
   py app.py
   ```

   The database tables are created automatically on first start. Keep the laptop running while billing.

4. On the laptop open `http://127.0.0.1:5000`. On a phone connected to the same Wi-Fi, open `http://LAPTOP-LOCAL-IP:5000` (find the laptop IPv4 address with `ipconfig`). Windows Firewall may ask to allow Python on your **Private** network; permit only the private network if you want phone access. This serves the app on your LAN only; do not configure router port forwarding.

## Use

- Add each product and your actual retail/wholesale prices and opening quantity. The app assigns an internal SKU and a unique Code 128 barcode per product type.
- Print barcode labels, verify label sizing in print preview, and apply the same label to each pack of that product type.
- Scan using a USB scanner in the barcode field, or use the phone camera button on a browser that supports the built-in `BarcodeDetector` API. Manual product selection is also available. A phone camera may require the browser to consider the page a secure context; on plain HTTP LAN addresses, support varies. The USB scanner/manual fallback works locally without that requirement.
- Save a bill to persist the invoice and deduct stock atomically. Receipts are printable. Daily invoice totals are on Sales report.

## Backups and security

Back up the `Crackers` database regularly from pgAdmin (right-click database → Backup). Keep the backup on a separate drive. The configured PostgreSQL password is the one supplied for your local setup; set a private password if you later change it. Set `FLASK_SECRET` to a random value and keep this service on your trusted local network.

The initial installation of Python packages requires internet unless you already have the packages or use offline installers. After setup, billing runs without internet. The project does not include the Mark Pyro Park catalogue because no catalogue file was present in the project folder; enter and verify your own product names and prices.
