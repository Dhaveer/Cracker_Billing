const cart = new Map();
const rows = document.getElementById('cartRows');
const barcodeInput = document.getElementById('barcode');
const rupees = n => '₹' + Number(n).toFixed(2);
function priceFor(p) { return Number(p.price); }
function addProduct(p) {
  const item = cart.get(p.id) || {...p, quantity: 0};
  item.quantity++; cart.set(p.id, item); renderCart();
}
async function lookup(code) {
  code = code.trim(); if (!code) return;
  try { const r = await fetch(`/api/product/${encodeURIComponent(code)}`); const p = await r.json(); if (!r.ok) throw Error(p.error || 'Product not found'); addProduct(p); }
  catch(e) { alert(e.message); }
  finally { barcodeInput.value = ''; barcodeInput.focus(); }
}
function renderCart() {
  const items = [...cart.values()];
  if (!items.length) rows.innerHTML = '<tr><td colspan="6" class="empty">Scan or select a product to begin.</td></tr>';
  else rows.innerHTML = items.map(p => `<tr><td>${escapeHtml(p.name)}</td><td>${escapeHtml(p.category || '')}</td><td>${rupees(priceFor(p))}</td><td><div class="qty"><button type="button" data-action="minus" data-id="${p.id}">−</button><input type="number" min="1" value="${p.quantity}" data-action="qty" data-id="${p.id}"><button type="button" data-action="plus" data-id="${p.id}">+</button></div></td><td>${rupees(priceFor(p) * p.quantity)}</td><td><button type="button" class="link-button danger" data-action="remove" data-id="${p.id}">Remove</button></td></tr>`).join('');
  const total = items.reduce((s,p) => s + priceFor(p) * p.quantity, 0);
  document.getElementById('grandTotal').textContent = rupees(total);
  document.getElementById('cart').value = items.map(p => `${p.id}:${p.quantity}`).join(',');
}
function escapeHtml(x) { return String(x).replace(/[&<>"']/g,c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
rows.addEventListener('click', e => { const b=e.target.closest('button[data-action]'); if(!b)return; const p=cart.get(Number(b.dataset.id)); if(b.dataset.action==='remove')cart.delete(p.id); else if(b.dataset.action==='plus')p.quantity++; else if(b.dataset.action==='minus'){p.quantity--;if(p.quantity<=0)cart.delete(p.id);} renderCart(); });
rows.addEventListener('change', e => {if(e.target.dataset.action==='qty'){const p=cart.get(Number(e.target.dataset.id));p.quantity=Math.max(1,Number(e.target.value)||1);renderCart();}});
let scanTimer;
barcodeInput.addEventListener('input', () => {
  clearTimeout(scanTimer);
  // Most scanners send a barcode as a rapid burst of keystrokes. The quiet
  // period supports scanners that do not append Enter; manual entry can use Enter.
  if (barcodeInput.value.trim().length >= 6) scanTimer = setTimeout(() => lookup(barcodeInput.value), 500);
});
barcodeInput.addEventListener('keydown', e => {if(e.key==='Enter'){e.preventDefault();clearTimeout(scanTimer);lookup(barcodeInput.value);}});
document.getElementById('saleForm').addEventListener('submit', e => {if(!cart.size){e.preventDefault();alert('Add a product first.');return;}document.getElementById('customerHidden').value=document.getElementById('customer').value;document.getElementById('customerPhoneHidden').value=document.getElementById('customerPhone').value;});
document.getElementById('cameraButton').addEventListener('click',()=>document.getElementById('camera').click());
document.getElementById('camera').addEventListener('change', async e=>{const file=e.target.files[0];if(!file)return;try{if(!('BarcodeDetector'in window))throw Error('This browser does not support built-in barcode scanning. Use a USB scanner or enter the code.');const detector=new BarcodeDetector({formats:['code_128','ean_13','ean_8','upc_a','upc_e','itf']});const bitmap=await createImageBitmap(file);const codes=await detector.detect(bitmap);if(!codes.length)throw Error('No barcode found. Try a clearer, closer photo.');lookup(codes[0].rawValue);}catch(err){alert(err.message);}finally{e.target.value='';}});
const searchInput = document.getElementById('productSearch');
const searchResults = document.getElementById('searchResults');
const catalogue = window.catalogue || [];
let matches = [];
const categoryButtons = document.getElementById('categoryButtons');
const categoryProducts = document.getElementById('categoryProducts');
let selectedCategory = '';
const categories = [...new Set(catalogue.map(p => p.category).filter(Boolean))].sort((a,b)=>a.localeCompare(b));
categoryButtons.innerHTML = categories.map((category,i) => `<button type="button" class="category-chip${i===0?' active':''}" data-category="${escapeHtml(category)}">${escapeHtml(category)} <span>${catalogue.filter(p=>p.category===category).length}</span></button>`).join('');
function showCategory(category) {
  selectedCategory = category;
  categoryButtons.querySelectorAll('.category-chip').forEach(b => b.classList.toggle('active', b.dataset.category===category));
  const items = catalogue.filter(p => p.category === category);
  categoryProducts.innerHTML = `<div class="product-choices">${items.map(p => `<button type="button" class="product-choice" data-product-id="${p.id}"><span class="product-number">${p.source_no ?? '•'}</span><span class="choice-name">${escapeHtml(p.name)}</span><strong>${rupees(priceFor(p))}</strong></button>`).join('')}</div>`;
}
categoryButtons.addEventListener('click', e => { const b=e.target.closest('[data-category]'); if(b)showCategory(b.dataset.category); });
categoryProducts.addEventListener('click', e => {const b=e.target.closest('[data-product-id]');if(!b)return;const p=catalogue.find(x=>x.id===Number(b.dataset.productId));if(p)addProduct(p);});
if (categories.length) showCategory(categories[0]);
function searchProducts() {
  const q = searchInput.value.trim().toLocaleLowerCase();
  if (!q) { matches = []; searchResults.innerHTML = ''; return; }
  matches = catalogue.filter(p => `${p.name} ${p.category} ${p.sku} ${p.barcode}`.toLocaleLowerCase().includes(q)).slice(0, 8);
  searchResults.innerHTML = matches.map((p,i) => `<button type="button" role="option" data-index="${i}" class="search-result"><span><strong>${escapeHtml(p.name)}</strong><small>${escapeHtml(p.category)} · ${escapeHtml(p.sku)}</small></span><b>${rupees(priceFor(p))}</b></button>`).join('') || '<div class="empty">No matching products.</div>';
}
searchInput.addEventListener('input', searchProducts);
searchInput.addEventListener('keydown', e => { if(e.key==='Enter' && matches.length){e.preventDefault();addProduct(matches[0]);searchInput.value='';searchProducts();} });
searchResults.addEventListener('click', e => {const b=e.target.closest('button[data-index]');if(!b)return;addProduct(matches[Number(b.dataset.index)]);searchInput.value='';searchProducts();searchInput.focus();});
document.getElementById('addSelected').addEventListener('click', () => {
  const id = Number(document.getElementById('productSelect').value);
  const product = catalogue.find(p => p.id === id);
  if (product) addProduct(product);
});
