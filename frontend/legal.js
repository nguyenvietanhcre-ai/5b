'use strict';
(() => {
  const allowed = new Set(['businessName','registrationNumber','taxId','address','representative','supportEmail','supportPhone','privacyEmail','complaintEmail']);
  fetch('/api/website/legal', {headers:{Accept:'application/json'}})
    .then(response => response.ok ? response.json() : null)
    .then(config => {
      if (!config || typeof config !== 'object') return;
      for (const [key,value] of Object.entries(config)) {
        if (!allowed.has(key) || typeof value !== 'string' || !value.trim()) continue;
        for (const node of document.querySelectorAll(`[data-legal="${key}"]`)) node.textContent = value.trim();
      }
    })
    .catch(() => {});
})();
