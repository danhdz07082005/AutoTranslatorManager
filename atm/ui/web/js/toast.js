/**
 * ATM.toast  Notification toast system
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
     * @param {string|boolean} [type] 'success', 'error', 'info', 'warning', or boolean for error fallback
     */
    show: function (message, type) {
      var toast = ATM.dom.byId('toast');
      var msg = ATM.dom.byId('toast-message');
      if (!toast || !msg) return;

      var isError = type === true || type === 'error';
      var isSuccess = type === 'success';
      var isWarning = type === 'warning';
      var isInfo = type === 'info' || type === false;

      var borderColor = 'var(--accent)';
      var textColor = 'var(--text-primary)';

      if (isError) {
          borderColor = 'var(--danger, #ef4444)';
          textColor = 'var(--danger, #ef4444)';
      } else if (isSuccess) {
          borderColor = 'var(--success, #10b981)';
          textColor = 'var(--success, #10b981)';
      } else if (isWarning) {
          borderColor = 'var(--warning, #f59e0b)';
          textColor = 'var(--warning, #f59e0b)';
      } else if (isInfo) {
          borderColor = '#3b82f6';
          textColor = '#3b82f6';
      }

      ATM.dom.text(msg, message);
      toast.style.borderColor = borderColor;
      msg.style.color = textColor;

      toast.classList.add('show');
      if (_timer) clearTimeout(_timer);
      _timer = setTimeout(function () {
        toast.classList.remove('show');
      }, 3000);
    },
  };
})(window.ATM);
