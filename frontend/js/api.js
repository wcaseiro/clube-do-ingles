const API_BASE = (() => {
  const host = window.location.hostname;
  const port = window.location.port;
  if ((port === '8080' || port === '8083') && host) {
    return `${window.location.protocol}//${host}:8008/api`;
  }
  return '/api';
})();

const store = {
  get token(){ return localStorage.getItem('token'); },
  set token(v){ localStorage.setItem('token', v); },
  clear(){ localStorage.removeItem('token'); localStorage.removeItem('user'); },
  get user(){ try { return JSON.parse(localStorage.getItem('user') || 'null'); } catch { return null; } },
  set user(v){ localStorage.setItem('user', JSON.stringify(v)); }
};

async function api(path, options = {}){
  const headers = options.headers || {};
  headers['Content-Type'] = headers['Content-Type'] || 'application/json';
  if(store.token) headers['Authorization'] = `Bearer ${store.token}`;
  const res = await fetch(API_BASE + path, { ...options, headers });
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if(!res.ok){ throw new Error(data?.detail || data?.message || 'Erro na requisição'); }
  return data;
}

function toast(msg, type='info'){
  const el=document.getElementById('toast');
  el.textContent=msg;
  el.className = `toast ${type}`;
  setTimeout(()=>el.classList.add('hidden'),3800);
}

function go(path){ history.pushState({}, '', path); render(); }
