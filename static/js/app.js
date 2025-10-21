// Core helpers
(function(){
  window.App = window.App || {};

  // Flash auto-dismiss
  App.autodismissAlerts = function(timeout){
    timeout = timeout || 4000;
    document.querySelectorAll('.alert').forEach(function(a){
      setTimeout(function(){ try{ a.classList.add('fade'); a.remove(); }catch(e){} }, timeout);
    });
  };

  // Simple CSV download from a table selector
  App.downloadTableAsCSV = function(selector, filename){
    const rows = Array.from(document.querySelectorAll(selector + ' tr'));
    const csv = rows.map(row => Array.from(row.querySelectorAll('th,td'))
      .map(cell => '"' + cell.innerText.replace(/"/g,'""') + '"').join(',')).join('\n');
    const blob = new Blob([csv], {type:'text/csv'});
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename || 'export.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Confirm form submits
  App.confirmSubmit = function(formSelector, message){
    const form = document.querySelector(formSelector);
    if(!form) return;
    form.addEventListener('submit', function(e){
      if(!confirm(message || 'Are you sure?')) e.preventDefault();
    });
  };

  // Date helpers
  App.formatMoney = function(n){ try { return '₹' + (Number(n)||0).toLocaleString(undefined,{maximumFractionDigits:2}); } catch(e){ return n; } };

  // Init
  document.addEventListener('DOMContentLoaded', function(){
    App.autodismissAlerts(3500);
  });
})();
