/**
 * ATM.toast — Notification toast system
 *
 * Usage:
 *   ATM.toast.show('Saved!');
 *   ATM.toast.show('Error!', true);
 */
(function (ATM) {
  'use strict';

  var _timer = null;

  ATM.Toast = {
    /**
     * Display a toast notification.
     * @param {string} message
     * @param {boolean} [isError=false]
     */
    show: function (message, isError) {
      var toast = ATM.dom.byId('toast');
      var msg = ATM.dom.byId('toast-message');
      if (!toast || !msg) return;

      ATM.dom.text(msg, message);
      toast.style.borderColor = isError ? 'var(--danger)' : 'var(--accent)';
      msg.style.color = isError ? 'var(--danger)' : 'var(--text-primary)';

      toast.classList.add('show');
      if (_timer) clearTimeout(_timer);
      _timer = setTimeout(function () {
        toast.classList.remove('show');
      }, 3000);
    },
  };
})(window.ATM);
