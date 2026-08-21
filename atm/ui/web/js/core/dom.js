window.ATM = window.ATM || {};
window.ATM.core = window.ATM.core || {};

/**
 * ATM.dom - Core DOM Helpers
 * Bảo vệ chống XSS bằng cách chỉ dùng textContent/createElement, không dùng innerHTML.
 */
(function() {
    window.ATM.dom = {
        /**
         * Tạo DOM Element an toàn
         */
        create: function(tagName, attributes = {}, children = []) {
            const el = document.createElement(tagName);
            
            for (const [key, value] of Object.entries(attributes)) {
                if (key === 'className') {
                    el.className = value;
                } else if (key === 'textContent') {
                    el.textContent = value;
                } else if (key === 'dataset') {
                    for (const [dKey, dValue] of Object.entries(value)) {
                        el.dataset[dKey] = dValue;
                    }
                } else if (key === 'style' && typeof value === 'object') {
                    Object.assign(el.style, value);
                } else {
                    el.setAttribute(key, value);
                }
            }
            
            for (const child of children) {
                if (typeof child === 'string') {
                    el.appendChild(document.createTextNode(child));
                } else if (child instanceof Node) {
                    el.appendChild(child);
                }
            }
            
            return el;
        },

        /**
         * Cập nhật text content an toàn
         */
        text: function(element, text) {
            if (element) element.textContent = text;
        },

        /**
         * Xóa sạch con của element
         */
        clear: function(element) {
            if (element) element.textContent = '';
        },

        /**
         * Lấy element theo ID an toàn
         */
        byId: function(id) {
            return document.getElementById(id);
        },

        /**
         * Lấy mảng elements theo Selector
         */
        query: function(selector, parent = document) {
            return Array.from(parent.querySelectorAll(selector));
        },

        /**
         * Gắn sự kiện (Event Delegation)
         */
        delegate: function(element, eventName, selector, handler) {
            if (!element) return;
            element.addEventListener(eventName, function(e) {
                const target = e.target.closest(selector);
                if (target && element.contains(target)) {
                    handler.call(target, e, target);
                }
            });
        },
        
        /**
         * Gắn sự kiện thông thường
         */
        on: function(element, eventName, handler) {
            if (!element) return;
            element.addEventListener(eventName, handler);
        }
    };
})();
