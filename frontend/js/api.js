const API_BASE = '/api';

const store = {
  get token(){ return localStorage.getItem('token'); },
  set token(v){ localStorage.setItem('token', v); },
  clear(){ localStorage.removeItem('token'); localStorage.removeItem('user'); },
  get user(){
    try {
      return JSON.parse(localStorage.getItem('user') || 'null');
    } catch {
      return null;
    }
  },
  set user(v){ localStorage.setItem('user', JSON.stringify(v)); }
};

async function api(path, options = {}){
  const headers = options.headers || {};
  headers['Content-Type'] = headers['Content-Type'] || 'application/json';

  if(store.token){
    headers['Authorization'] = `Bearer ${store.token}`;
  }

  const res = await fetch(API_BASE + path, {
    ...options,
    headers
  });

  const text = await res.text();
  let data = null;

  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }

  if(!res.ok){
    throw new Error(data?.detail || data?.message || 'Erro na requisição');
  }

  return data;
}

function toast(msg, type='info'){
  const el = document.getElementById('toast');

  if(!el){
    alert(msg);
    return;
  }

  el.textContent = msg;
  el.className = `toast ${type}`;
  el.classList.remove('hidden');

  setTimeout(() => {
    el.classList.add('hidden');
  }, 3800);
}

function go(path){
  history.pushState({}, '', path);
  render();
}
