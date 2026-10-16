import os
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import psycopg
from psycopg.rows import dict_row
from flask import Flask, abort, flash, redirect, render_template, request, url_for, Response

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "local-only-change-me")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin@localhost:5432/Crackers")


def db():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_db():
    with db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id BIGSERIAL PRIMARY KEY, sku TEXT UNIQUE NOT NULL, barcode TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL, pack_size TEXT NOT NULL DEFAULT '', category TEXT NOT NULL DEFAULT '',
            purchase_price NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (purchase_price >= 0),
            retail_price NUMERIC(12,2) NOT NULL CHECK (retail_price >= 0),
            wholesale_price NUMERIC(12,2) NOT NULL CHECK (wholesale_price >= 0),
            stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0), active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS sales (
            id BIGSERIAL PRIMARY KEY, invoice_no TEXT UNIQUE NOT NULL,
            sale_type TEXT NOT NULL CHECK (sale_type IN ('Retail','Wholesale')),
            customer TEXT NOT NULL DEFAULT '', discount NUMERIC(12,2) NOT NULL DEFAULT 0,
            total NUMERIC(12,2) NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS sale_items (
            id BIGSERIAL PRIMARY KEY, sale_id BIGINT NOT NULL REFERENCES sales(id),
            product_id BIGINT NOT NULL REFERENCES products(id), product_name TEXT NOT NULL,
            barcode TEXT NOT NULL, quantity INTEGER NOT NULL CHECK (quantity > 0),
            unit_price NUMERIC(12,2) NOT NULL, line_total NUMERIC(12,2) NOT NULL
        );
        CREATE TABLE IF NOT EXISTS stock_movements (
            id BIGSERIAL PRIMARY KEY, product_id BIGINT NOT NULL REFERENCES products(id),
            quantity_delta INTEGER NOT NULL, note TEXT NOT NULL DEFAULT '', created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """)


def money(value, field):
    try:
        amount = Decimal(value or "0")
        if not amount.is_finite() or amount < 0:
            raise InvalidOperation
        return amount.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raise ValueError(f"Enter a valid non-negative amount for {field}.")


@app.get("/")
def checkout():
    with db() as conn:
        products = conn.execute("SELECT * FROM products WHERE active ORDER BY name").fetchall()
    catalogue = [{"id": p["id"], "sku": p["sku"], "barcode": p["barcode"], "name": p["name"],
                 "pack_size": p["pack_size"], "retail_price": str(p["retail_price"]),
                 "wholesale_price": str(p["wholesale_price"]), "stock": p["stock"]} for p in products]
    return render_template("checkout.html", products=products, catalogue=catalogue, today=date.today())


@app.get("/products")
def products_page():
    with db() as conn:
        products = conn.execute("SELECT * FROM products ORDER BY active DESC, name").fetchall()
        edit_id = request.args.get("edit", "")
        editing = conn.execute("SELECT * FROM products WHERE id=%s", (edit_id,)).fetchone() if edit_id.isdigit() else None
    return render_template("products.html", products=products, editing=editing)


@app.post("/products")
def save_product():
    try:
        name = request.form.get("name", "").strip()
        if not name:
            raise ValueError("Product name is required.")
        retail = money(request.form.get("retail_price"), "retail price")
        wholesale = money(request.form.get("wholesale_price"), "wholesale price")
        cost = money(request.form.get("purchase_price"), "purchase price")
        stock = int(request.form.get("stock", "0"))
        if stock < 0:
            raise ValueError("Stock cannot be negative.")
        with db() as conn:
            product_id = request.form.get("id")
            if product_id:
                old = conn.execute("SELECT stock FROM products WHERE id=%s FOR UPDATE", (product_id,)).fetchone()
                if not old:
                    abort(404)
                conn.execute("""UPDATE products SET name=%s,pack_size=%s,category=%s,purchase_price=%s,
                    retail_price=%s,wholesale_price=%s,stock=%s,active=%s WHERE id=%s""",
                    (name, request.form.get("pack_size", "").strip(), request.form.get("category", "").strip(), cost, retail, wholesale, stock, request.form.get("active") == "on", product_id))
                delta = stock - old["stock"]
                if delta:
                    conn.execute("INSERT INTO stock_movements(product_id,quantity_delta,note) VALUES (%s,%s,'Product edit')", (product_id, delta))
            else:
                next_id = conn.execute("SELECT nextval(pg_get_serial_sequence('products','id')) AS id").fetchone()["id"]
                sku = f"CRK{next_id:06d}"
                barcode = f"20{next_id:010d}"
                conn.execute("""INSERT INTO products(id,sku,barcode,name,pack_size,category,purchase_price,retail_price,wholesale_price,stock)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", (next_id, sku, barcode, name, request.form.get("pack_size", "").strip(), request.form.get("category", "").strip(), cost, retail, wholesale, stock))
                if stock:
                    conn.execute("INSERT INTO stock_movements(product_id,quantity_delta,note) VALUES (%s,%s,'Opening stock')", (next_id, stock))
        flash("Product saved. Print its barcode label and apply the same code to each pack of this product.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    except psycopg.errors.UniqueViolation:
        flash("That product or barcode already exists. Refresh the page and try again.", "error")
    return redirect(url_for("products_page"))


@app.post("/products/<int:product_id>/toggle")
def toggle_product(product_id):
    with db() as conn:
        conn.execute("UPDATE products SET active=NOT active WHERE id=%s", (product_id,))
    return redirect(url_for("products_page"))


@app.get("/api/product/<barcode>")
def product_by_barcode(barcode):
    with db() as conn:
        product = conn.execute("SELECT id,sku,barcode,name,pack_size,retail_price,wholesale_price,stock FROM products WHERE barcode=%s AND active", (barcode,)).fetchone()
    if not product:
        return {"error": "No active product found for that barcode."}, 404
    return {k: (str(v) if isinstance(v, Decimal) else v) for k, v in product.items()}


@app.get("/api/product-by-id/<int:product_id>")
def product_by_id(product_id):
    with db() as conn:
        product = conn.execute("SELECT id,sku,barcode,name,pack_size,retail_price,wholesale_price,stock FROM products WHERE id=%s AND active", (product_id,)).fetchone()
    if not product:
        return {"error": "No active product found."}, 404
    return {k: (str(v) if isinstance(v, Decimal) else v) for k, v in product.items()}


@app.get("/barcode/<barcode>.svg")
def barcode_svg(barcode):
    from barcode import Code128
    from barcode.writer import SVGWriter
    with db() as conn:
        product = conn.execute("SELECT name FROM products WHERE barcode=%s AND active", (barcode,)).fetchone()
    if not product:
        abort(404)
    svg = Code128(barcode, writer=SVGWriter()).render(options={"module_width": 0.25, "module_height": 12, "quiet_zone": 2, "font_size": 8, "text_distance": 2, "write_text": True})
    return Response(svg, mimetype="image/svg+xml")


@app.post("/sales")
def create_sale():
    try:
        sale_type = request.form.get("sale_type", "Retail")
        if sale_type not in ("Retail", "Wholesale"):
            raise ValueError("Choose retail or wholesale billing.")
        discount = money(request.form.get("discount"), "discount")
        cart = request.form.get("cart", "")
        quantities = {}
        for part in cart.split(","):
            if part:
                pid, qty = part.split(":", 1)
                quantities[int(pid)] = quantities.get(int(pid), 0) + int(qty)
        if not quantities or any(q <= 0 for q in quantities.values()):
            raise ValueError("Add at least one product with a valid quantity.")
        with db() as conn:
            items, subtotal = [], Decimal("0.00")
            for pid, qty in quantities.items():
                p = conn.execute("SELECT * FROM products WHERE id=%s AND active FOR UPDATE", (pid,)).fetchone()
                if not p:
                    raise ValueError("A product in the cart is unavailable. Please refresh and try again.")
                if p["stock"] < qty:
                    raise ValueError(f"Not enough stock for {p['name']}. Available: {p['stock']}.")
                price = p["retail_price"] if sale_type == "Retail" else p["wholesale_price"]
                line_total = price * qty
                subtotal += line_total
                items.append((p, qty, price, line_total))
            if discount > subtotal:
                raise ValueError("Discount cannot exceed the bill subtotal.")
            total = subtotal - discount
            invoice = "INV-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            sale = conn.execute("INSERT INTO sales(invoice_no,sale_type,customer,discount,total) VALUES (%s,%s,%s,%s,%s) RETURNING id",
                                (invoice, sale_type, request.form.get("customer", "").strip(), discount, total)).fetchone()
            for p, qty, price, line_total in items:
                conn.execute("INSERT INTO sale_items(sale_id,product_id,product_name,barcode,quantity,unit_price,line_total) VALUES (%s,%s,%s,%s,%s,%s,%s)", (sale["id"], p["id"], p["name"], p["barcode"], qty, price, line_total))
                conn.execute("UPDATE products SET stock=stock-%s WHERE id=%s", (qty, p["id"]))
                conn.execute("INSERT INTO stock_movements(product_id,quantity_delta,note) VALUES (%s,%s,%s)", (p["id"], -qty, invoice))
        return redirect(url_for("receipt", sale_id=sale["id"]))
    except (ValueError, InvalidOperation) as exc:
        flash(str(exc), "error")
        return redirect(url_for("checkout"))


@app.get("/receipt/<int:sale_id>")
def receipt(sale_id):
    with db() as conn:
        sale = conn.execute("SELECT * FROM sales WHERE id=%s", (sale_id,)).fetchone()
        if not sale:
            abort(404)
        items = conn.execute("SELECT * FROM sale_items WHERE sale_id=%s ORDER BY id", (sale_id,)).fetchall()
    return render_template("receipt.html", sale=sale, items=items)


@app.get("/reports")
def reports():
    day = request.args.get("day", date.today().isoformat())
    with db() as conn:
        sales = conn.execute("SELECT * FROM sales WHERE created_at::date=%s ORDER BY created_at DESC", (day,)).fetchall()
        totals = conn.execute("SELECT COALESCE(SUM(total),0) AS total, COUNT(*) AS count FROM sales WHERE created_at::date=%s", (day,)).fetchone()
    return render_template("reports.html", sales=sales, totals=totals, day=day)


@app.get("/labels")
def labels():
    with db() as conn:
        products = conn.execute("SELECT * FROM products WHERE active ORDER BY name").fetchall()
    return render_template("labels.html", products=products)


@app.get("/health")
def health():
    with db() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok", "database": "postgresql"}


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
