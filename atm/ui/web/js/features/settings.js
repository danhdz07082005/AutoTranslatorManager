window.ATM = window.ATM || {};

window.ATM.Settings = (function() {
    const PROVIDER_METADATA = {
        gemini: {
            name: 'Google Gemini',
            defaultUrl: 'https://generativelanguage.googleapis.com/v1beta/openai',
            defaultModel: 'gemini-2.5-flash',
            models: ['gemini-2.5-flash', 'gemini-3.8-flash', 'gemini-3.1-pro', 'gemini-2.0-flash'],
            getKeyUrl: 'https://aistudio.google.com/app/apikey',
            keyPlaceholder: 'AIzaSy...'
        },
        deepseek: {
            name: 'DeepSeek',
            defaultUrl: 'https://api.deepseek.com',
            defaultModel: 'deepseek-chat',
            models: ['deepseek-chat', 'deepseek-reasoner', 'deepseek-v3', 'deepseek-r1', 'deepseek-v4'],
            getKeyUrl: 'https://platform.deepseek.com/api_keys',
            keyPlaceholder: 'sk-...'
        },
        openai: {
            name: 'OpenAI (ChatGPT)',
            defaultUrl: 'https://api.openai.com/v1',
            defaultModel: 'gpt-4o-mini',
            models: ['gpt-4o-mini', 'gpt-4o', 'gpt-5.6-sol', 'gpt-6-astra', 'o3-mini'],
            getKeyUrl: 'https://platform.openai.com/api-keys',
            keyPlaceholder: 'sk-proj-...'
        },
        claude: {
            name: 'Anthropic Claude',
            defaultUrl: 'https://api.anthropic.com/v1',
            defaultModel: 'claude-3-7-sonnet-20250219',
            models: ['claude-3-7-sonnet-20250219', 'claude-3-5-haiku-20241022', 'claude-5-fable', 'claude-3-5-sonnet-20241022'],
            getKeyUrl: 'https://console.anthropic.com/settings/keys',
            keyPlaceholder: 'sk-ant-...'
        },
        kimi: {
            name: 'Moonshot Kimi',
            defaultUrl: 'https://api.moonshot.cn/v1',
            defaultModel: 'moonshot-v1-8k',
            models: ['moonshot-v1-8k', 'moonshot-v1-32k', 'kimi-latest'],
            getKeyUrl: 'https://platform.moonshot.cn/console/api-keys',
            keyPlaceholder: 'sk-...'
        },
        custom_llm: {
            name: 'Custom / Local LLM',
            defaultUrl: 'http://localhost:11434/v1',
            defaultModel: 'qwen2.5:7b',
            models: ['qwen2.5:7b', 'llama3.3:70b', 'deepseek-r1:8b'],
            getKeyUrl: 'https://ollama.com',
            keyPlaceholder: 'Optional (e.g. Ollama no key needed)'
        }
    };

    const AI_PROVIDERS = ['gemini', 'deepseek', 'openai', 'claude', 'kimi', 'custom_llm'];

    let currentProvider = 'gemini';
    let currentSettings = {};
    let isEditingKey = false;
    let testResultTimeout = null;
    let isStudioBusy = false;
    let activeOperation = null; // 'fetch' | 'test' | 'save' | 'clear'
    let activeOperationProvider = null;

    const setStudioBusy = (busy, operation = null, provider = null, statusMsg = null) => {
        isStudioBusy = Boolean(busy);
        activeOperation = busy ? operation : null;
        activeOperationProvider = busy ? provider : null;

        const testBtn = document.getElementById('studio-test-btn');
        const saveBtn = document.getElementById('studio-save-btn');
        const clearBtn = document.getElementById('studio-clear-btn');
        const changeKeyBtn = document.getElementById('studio-change-key-btn');
        const fetchModelsBtn = document.getElementById('studio-fetch-models-btn');
        const resetModelBtn = document.getElementById('studio-reset-model-btn');
        const modelInput = document.getElementById('studio-model');
        const keyInput = document.getElementById('studio-api-key');
        const urlInput = document.getElementById('studio-base-url');

        if (busy) {
            if (testBtn) testBtn.disabled = true;
            if (saveBtn) saveBtn.disabled = true;
            if (clearBtn) clearBtn.disabled = true;
            if (changeKeyBtn) changeKeyBtn.disabled = true;
            if (fetchModelsBtn) fetchModelsBtn.disabled = true;
            if (resetModelBtn) resetModelBtn.disabled = true;
            if (modelInput) modelInput.disabled = true;
            if (keyInput) keyInput.disabled = true;
            if (urlInput) urlInput.disabled = true;

            document.querySelectorAll('.model-pill').forEach(p => p.disabled = true);
            document.querySelectorAll('.btn-chip-remove').forEach(b => b.disabled = true);
            document.querySelectorAll('.studio-tab').forEach(t => t.classList.add('is-studio-locked'));

            if (statusMsg && window.ATM.Toast && operation !== 'test' && operation !== 'fetch') {
                window.ATM.Toast.show(statusMsg, 'info');
            }
        } else {
            document.querySelectorAll('.model-pill').forEach(p => p.disabled = false);
            document.querySelectorAll('.btn-chip-remove').forEach(b => b.disabled = false);
            document.querySelectorAll('.studio-tab').forEach(t => t.classList.remove('is-studio-locked'));

            if (testBtn) testBtn.disabled = false;
            if (saveBtn) saveBtn.disabled = false;
            if (clearBtn) clearBtn.disabled = false;
            if (changeKeyBtn) changeKeyBtn.disabled = false;
            if (fetchModelsBtn) fetchModelsBtn.disabled = false;
            if (resetModelBtn) resetModelBtn.disabled = false;
            if (modelInput) modelInput.disabled = false;
            if (urlInput) urlInput.disabled = false;

            renderProviderContext(currentProvider);
        }
    };

    const detectKeyMismatch = (provider, key) => {
        if (!key) return null;
        const cleanKey = key.trim();
        const prov = (provider || '').toLowerCase();
        const provName = PROVIDER_METADATA[prov] ? PROVIDER_METADATA[prov].name : prov.toUpperCase();
        if (prov !== 'gemini' && cleanKey.startsWith('AIzaSy')) {
            return window.ATM.i18n ? window.ATM.i18n.t('plugins.warning_gemini_key', { provider: provName }) : `This looks like a Google Gemini API Key (AIzaSy...), not for ${provName}!`;
        }
        if (prov !== 'claude' && cleanKey.startsWith('sk-ant-')) {
            return window.ATM.i18n ? window.ATM.i18n.t('plugins.warning_claude_key', { provider: provName }) : `This looks like an Anthropic Claude API Key (sk-ant-...), not for ${provName}!`;
        }
        if (cleanKey.endsWith(':fx') && prov !== 'deepl') {
            return window.ATM.i18n ? window.ATM.i18n.t('plugins.warning_deepl_key', { provider: provName }) : `This looks like a DeepL Free API Key (:fx), not for ${provName}!`;
        }
        return null;
    };

    const detectKeyFormatWarning = (provider, key) => {
        if (!key) return null;
        const cleanKey = key.trim();
        const prov = (provider || '').toLowerCase();
        if (prov === 'custom_llm') return null;

        // 1. Kiểm tra dán nhầm key giữa các hãng trước
        const mismatch = detectKeyMismatch(prov, cleanKey);
        if (mismatch) return mismatch;

        // 2. Cảnh báo định dạng và độ dài (Quy chuẩn 2026)
        const provName = PROVIDER_METADATA[prov] ? PROVIDER_METADATA[prov].name : prov.toUpperCase();
        const genericWarning = window.ATM.i18n 
            ? window.ATM.i18n.t('plugins.warning_key_format', { provider: provName })
            : `This doesn't seem to match the typical API Key format for ${provName}. Please verify.`;

        if (prov === 'gemini') {
            // Google Cloud / AI Studio keys start with AIzaSy and are ~39 chars (>= 35)
            if (!cleanKey.startsWith('AIzaSy') || cleanKey.length < 35) {
                return genericWarning;
            }
        } else if (prov === 'claude') {
            // Anthropic Claude keys start with sk-ant- and are long (>= 50, usually ~108 chars)
            if (!cleanKey.startsWith('sk-ant-') || cleanKey.length < 50) {
                return genericWarning;
            }
        } else if (['openai', 'deepseek', 'kimi'].includes(prov)) {
            // OpenAI (sk- / sk-proj-), DeepSeek (sk- 32 chars), Kimi (sk- ~48 chars)
            if (!cleanKey.startsWith('sk-') || cleanKey.length < 30) {
                return genericWarning;
            }
        } else if (prov === 'deepl') {
            // DeepL UUID (36 chars) or UUID:fx (39 chars)
            if (cleanKey.length < 30) {
                return genericWarning;
            }
        }
        return null;
    };

    const validateKeyFormat = (provider, key) => {
        if (!key) return { valid: false, message: window.ATM.i18n ? window.ATM.i18n.t('error.api_key_missing') : 'API Key is required' };
        const cleanKey = key.trim();
        const prov = (provider || '').toLowerCase();
        const provName = PROVIDER_METADATA[prov] ? PROVIDER_METADATA[prov].name : prov.toUpperCase();

        // Cảnh báo mềm khi phát hiện dán nhầm API key của hãng khác (Mismatch) - không chặn lưu
        const mismatchMsg = detectKeyMismatch(prov, cleanKey);
        if (mismatchMsg) {
            return { valid: true, warning: mismatchMsg };
        }

        // Chặn nhập chuỗi rác quá ngắn dưới 5 ký tự (như "a", "123")
        if (prov !== 'custom_llm' && cleanKey.length < 5) {
            return { 
                valid: false, 
                message: window.ATM.i18n ? window.ATM.i18n.t('error.key_too_short_5') : 'API Key is too short (minimum 5 characters)!' 
            };
        }

        return { valid: true };
    };

    const detectModelMismatch = (provider, model) => {
        if (!model) return null;
        const m = model.trim().toLowerCase();
        const prov = (provider || '').toLowerCase();
        if (prov === 'custom_llm') return null;

        let detectedProv = null;
        let detectedName = null;

        if (m.startsWith('gemini-') || m.startsWith('models/gemini')) {
            detectedProv = 'gemini';
            detectedName = 'Google Gemini';
        } else if (m.startsWith('claude-')) {
            detectedProv = 'claude';
            detectedName = 'Anthropic Claude';
        } else if (m.startsWith('deepseek-')) {
            detectedProv = 'deepseek';
            detectedName = 'DeepSeek';
        } else if (m.startsWith('moonshot-') || m.startsWith('kimi-')) {
            detectedProv = 'kimi';
            detectedName = 'Moonshot Kimi';
        } else if (m.startsWith('gpt-') || m.startsWith('o1-') || m.startsWith('o3-') || m.startsWith('o4-') || m.startsWith('chatgpt-')) {
            detectedProv = 'openai';
            detectedName = 'OpenAI';
        }

        if (detectedProv && detectedProv !== prov) {
            const currentName = PROVIDER_METADATA[prov] ? PROVIDER_METADATA[prov].name : prov.toUpperCase();
            return {
                detectedProvider: detectedProv,
                detectedName: detectedName,
                warning: window.ATM.i18n 
                    ? window.ATM.i18n.t('plugins.warning_model_mismatch', { model: model.trim(), detected: detectedName, provider: currentName })
                    : `Model '${model.trim()}' appears to belong to ${detectedName}, not ${currentName}!`
            };
        }
        return null;
    };

    const suggestModelName = (provider, rawInput) => {
        if (!rawInput) return null;
        const prov = (provider || '').toLowerCase();
        const rawTrim = rawInput.trim();
        const rawLower = rawTrim.toLowerCase();
        const text = rawLower.replace(/[,_]/g, ' ');
        if (!text) return null;

        // Guard 1: If input is already an exact match in the provider's known models list, NEVER suggest
        const meta = PROVIDER_METADATA[prov];
        if (meta && meta.models && meta.models.some(m => m.toLowerCase() === rawLower || m.toLowerCase() === text)) {
            return null;
        }

        // Guard 2: If input is an official dated/versioned identifier, NEVER suggest
        if (/^claude-[a-z0-9\.\-]+(-\d{8}|-latest)$/i.test(rawTrim) || 
            /^gpt-[a-z0-9\.\-]+(-\d{4}-\d{2}-\d{2}|-preview)$/i.test(rawTrim) ||
            /^gemini-[a-z0-9\.\-]+(-\d{3})$/i.test(rawTrim)) {
            return null;
        }

        if (prov === 'openai') {
            if (text.includes('6') && text.includes('astra')) return 'gpt-6-astra';
            if (text.includes('5') && (text.includes('6') || text.includes('sol'))) return 'gpt-5.6-sol';
            if (text.includes('4o') && text.includes('mini')) return 'gpt-4o-mini';
            if (text.includes('o3') || text.includes('o-3')) return 'o3-mini';
            if (text.includes('o1') || text.includes('o-1')) return 'o1-mini';
            if (text.includes('4o') || text === '4 o' || text === 'gpt 4o') return 'gpt-4o';
            if (text === 'gpt 5' || text === 'gpt-5' || text === 'gpt5') return 'gpt-5';
        } else if (prov === 'gemini') {
            if (text.includes('3.8') || text.includes('3 8') || text.includes('3-8')) return 'gemini-3.8-flash';
            if (text.includes('3.1') || text.includes('3 1') || text.includes('3-1')) return 'gemini-3.1-pro';
            if (text.includes('2.5') || text.includes('2 5') || text.includes('2-5')) return 'gemini-2.5-flash';
            if (text.includes('2.0') || text.includes('2 0') || text.includes('2 flash') || text.includes('2-0')) return 'gemini-2.0-flash';
            if (text.includes('1.5') || text.includes('1 5') || text.includes('1-5')) {
                if (text.includes('pro')) return 'gemini-1.5-pro';
                return 'gemini-1.5-flash';
            }
            if (text === 'flash' || text === 'gemini flash') return 'gemini-2.5-flash';
            if (text === 'pro' || text === 'gemini pro') return 'gemini-3.1-pro';
        } else if (prov === 'claude') {
            if (text.includes('3.7') || text.includes('3 7') || text.includes('3-7')) return 'claude-3-7-sonnet-20250219';
            if (text.includes('fable') || text.includes('claude 5') || text.includes('claude-5') || text.includes('5-fable') || text.includes('5 fable')) return 'claude-5-fable';
            if (text.includes('3.5') && text.includes('sonnet')) return 'claude-3-5-sonnet-20241022';
            if (text.includes('3.5') && text.includes('haiku')) return 'claude-3-5-haiku-20241022';
            if (text === 'haiku' || text === 'claude haiku') return 'claude-3-5-haiku-20241022';
            if (text === 'sonnet' || text === 'claude sonnet') return 'claude-3-7-sonnet-20250219';
        } else if (prov === 'deepseek') {
            if (text.includes('r1') || text.includes('r-1') || text === 'r 1') return 'deepseek-r1';
            if (text.includes('v3') || text.includes('v-3')) return 'deepseek-v3';
            if (text.includes('v4') || text.includes('v-4')) return 'deepseek-v4';
            if (text.includes('reason')) return 'deepseek-reasoner';
            if (text.includes('chat') || text === 'deepseek' || text === 'deep seek') return 'deepseek-chat';
        } else if (prov === 'kimi') {
            if (text.includes('32k') || text.includes('32')) return 'moonshot-v1-32k';
            if (text.includes('8k') || text.includes('8')) return 'moonshot-v1-8k';
            if (text.includes('latest') || text === 'kimi') return 'kimi-latest';
        } else if (prov === 'custom_llm') {
            if (text.includes('qwen')) return 'qwen2.5:7b';
            if (text.includes('llama')) return 'llama3.3:70b';
            if (text.includes('r1')) return 'deepseek-r1:8b';
        }
        return null;
    };

    const checkModelWarning = (provider, model) => {
        const warnBox = document.getElementById('studio-model-warning');
        const warnText = document.getElementById('studio-model-warning-text');
        if (!warnBox) return null;
        if (!model) {
            warnBox.style.display = 'none';
            if (warnText) warnText.textContent = '';
            return null;
        }

        // 1. Kiểm tra chéo hãng (Cross-Provider Mismatch)
        const mismatch = detectModelMismatch(provider, model);
        if (mismatch) {
            if (warnText) warnText.textContent = mismatch.warning;
            warnBox.style.display = 'flex';
            return mismatch;
        }

        // 2. Gợi ý thông minh hoặc cảnh báo ký tự lạ (dấu phẩy, dấu cách)
        const trimmed = model.trim().toLowerCase();
        const suggestion = suggestModelName(provider, model);
        if (/[,\s]/.test(model) || (suggestion && suggestion !== trimmed)) {
            if (suggestion && suggestion !== trimmed) {
                const suggestText = window.ATM.i18n ? window.ATM.i18n.t('plugins.suggest_model') : 'Did you mean: ';
                warnText.replaceChildren();
                const span = document.createElement('span');
                span.textContent = suggestText;
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'btn-suggest-pill';
                btn.textContent = suggestion;
                btn.addEventListener('click', async () => {
                    const input = document.getElementById('studio-model');
                    if (input) {
                        input.value = suggestion;
                        currentSettings[`${currentProvider}_model`] = suggestion;
                        checkModelWarning(provider, suggestion);
                        await saveStudioConfig();
                    }
                });
                warnText.appendChild(span);
                warnText.appendChild(btn);
                warnBox.style.display = 'flex';
                return { warning: suggestText + suggestion, suggestion };
            } else if (/[,\s]/.test(model)) {
                const msg = window.ATM.i18n ? window.ATM.i18n.t('plugins.invalid_model_chars') : 'Model name cannot contain spaces or commas.';
                if (warnText) warnText.textContent = msg;
                warnBox.style.display = 'flex';
                return { warning: msg };
            }
        }

        warnBox.style.display = 'none';
        if (warnText) warnText.textContent = '';
        return null;
    };

    const triggerInputError = (inputEl, message) => {
        if (!inputEl) return;
        inputEl.classList.remove('input-shake-error');
        void inputEl.offsetWidth;
        inputEl.classList.add('input-shake-error');
        setTimeout(() => {
            if (inputEl) inputEl.classList.remove('input-shake-error');
        }, 600);

        if (message && window.ATM.Toast) {
            window.ATM.Toast.show(message, 'error');
        }
    };

    const resetTestResult = () => {
        if (testResultTimeout) {
            clearTimeout(testResultTimeout);
            testResultTimeout = null;
        }
        const resultSpan = document.getElementById('studio-test-result');
        if (resultSpan) {
            resultSpan.className = 'test-latency';
            resultSpan.textContent = '';
        }
    };

    const renderActiveChips = () => {
        const container = document.getElementById('studio-active-chips');
        if (!container) return;

        container.replaceChildren();

        const configuredProviders = AI_PROVIDERS.filter(prov => {
            if (prov === 'custom_llm') {
                return Boolean(currentSettings.custom_llm_model && currentSettings.custom_llm_base_url);
            }
            return Boolean(currentSettings[`${prov}_api_key_configured`]);
        });

        if (configuredProviders.length === 0) {
            const hint = document.createElement('div');
            hint.className = 'no-active-profiles-hint';
            hint.textContent = window.ATM.i18n ? window.ATM.i18n.t('plugins.no_active_profiles') : 'No AI profiles configured yet. Enter an API Key above to activate.';
            container.appendChild(hint);
            return;
        }

        configuredProviders.forEach(prov => {
            const meta = PROVIDER_METADATA[prov];
            const configuredModel = currentSettings[`${prov}_model`] || meta.defaultModel;

            const chip = document.createElement('span');
            chip.className = 'active-profile-chip is-configured' + (prov === currentProvider ? ' active-current' : '');
            
            const dot = document.createElement('span');
            dot.className = 'profile-status-dot';
            chip.appendChild(dot);

            const nameSpan = document.createElement('span');
            nameSpan.textContent = `${meta.name} (${configuredModel})`;
            chip.appendChild(nameSpan);

            // Button remove configuration directly from chip
            const removeBtn = document.createElement('button');
            removeBtn.type = 'button';
            removeBtn.className = 'btn-chip-remove';
            removeBtn.title = window.ATM.i18n ? window.ATM.i18n.t('plugins.remove_profile_tooltip') : 'Remove configuration';
            removeBtn.textContent = '×';
            removeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                if (isStudioBusy) {
                    if (window.ATM.Toast) {
                        window.ATM.Toast.show(window.ATM.i18n ? window.ATM.i18n.t('plugins.operation_in_progress') : 'Operation in progress, please wait...', 'warning');
                    }
                    return;
                }
                clearStudioConfig(prov);
            });
            chip.appendChild(removeBtn);

            chip.addEventListener('click', () => {
                if (isStudioBusy) {
                    if (window.ATM.Toast) {
                        window.ATM.Toast.show(window.ATM.i18n ? window.ATM.i18n.t('plugins.operation_in_progress') : 'Operation in progress, please wait...', 'warning');
                    }
                    return;
                }
                isEditingKey = false;
                renderProviderContext(prov);
            });

            container.appendChild(chip);
        });
    };

    const syncDraftInputs = () => {
        const mInput = document.getElementById('studio-model');
        const uInput = document.getElementById('studio-base-url');
        if (mInput && mInput.value.trim() && currentProvider) {
            currentSettings[`${currentProvider}_model`] = mInput.value.trim();
        }
        if (uInput && uInput.value.trim() && currentProvider) {
            currentSettings[`${currentProvider}_base_url`] = uInput.value.trim();
        }
    };

    const renderProviderContext = (provider) => {
        if (currentProvider && currentProvider !== provider) {
            syncDraftInputs();
        }
        currentProvider = provider;
        const meta = PROVIDER_METADATA[provider] || PROVIDER_METADATA.gemini;

        // Sync tabs
        const tabsContainer = document.getElementById('studio-provider-tabs');
        if (tabsContainer) {
            tabsContainer.querySelectorAll('.studio-tab').forEach(tab => {
                if (tab.dataset.provider === provider) {
                    tab.classList.add('active');
                } else {
                    tab.classList.remove('active');
                }
            });
        }

        // Sync active badge
        const activeBadge = document.getElementById('studio-active-badge');
        if (activeBadge) {
            activeBadge.textContent = meta.name;
        }

        // Sync Base URL
        const urlInput = document.getElementById('studio-base-url');
        if (urlInput) {
            urlInput.value = currentSettings[`${provider}_base_url`] || meta.defaultUrl;
        }

        // Sync Model input
        const modelInput = document.getElementById('studio-model');
        if (modelInput) {
            modelInput.value = currentSettings[`${provider}_model`] || meta.defaultModel;
        }

        // Sync Datalist
        const datalist = document.getElementById('studio-models-list');
        if (datalist) {
            datalist.replaceChildren();
            meta.models.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m;
                datalist.appendChild(opt);
            });
        }

        // Sync Model Pills
        const pillsContainer = document.getElementById('studio-model-pills');
        if (pillsContainer) {
            pillsContainer.replaceChildren();
            meta.models.forEach(m => {
                const pill = document.createElement('button');
                pill.type = 'button';
                pill.className = 'model-pill';
                pill.textContent = m;
                pill.addEventListener('click', async () => {
                    if (isStudioBusy) {
                        if (window.ATM.Toast) {
                            window.ATM.Toast.show(window.ATM.i18n ? window.ATM.i18n.t('plugins.operation_in_progress') : 'Operation in progress, please wait...', 'warning');
                        }
                        return;
                    }
                    if (modelInput) {
                        modelInput.value = m;
                        currentSettings[`${currentProvider}_model`] = m;
                        checkModelWarning(currentProvider, m);
                        const isCustomLlm = currentProvider === 'custom_llm';
                        const isConfigured = isCustomLlm 
                            ? Boolean(currentSettings.custom_llm_model && currentSettings.custom_llm_base_url)
                            : Boolean(currentSettings[`${currentProvider}_api_key_configured`]);
                        if (isConfigured) {
                            await saveStudioConfig();
                        }
                    }
                });
                pillsContainer.appendChild(pill);
            });
        }

        // Sync Reset Model Button
        const resetModelBtn = document.getElementById('studio-reset-model-btn');
        if (resetModelBtn) {
            resetModelBtn.disabled = isStudioBusy;
        }

        // Sync Get Free Key Link
        const link = document.getElementById('studio-get-key-link');
        if (link) {
            link.href = meta.getKeyUrl;
        }

        // Sync API Key input & Locking State
        const keyInput = document.getElementById('studio-api-key');
        const statusBadge = document.getElementById('studio-status-badge');
        const saveBtn = document.getElementById('studio-save-btn');
        const changeKeyBtn = document.getElementById('studio-change-key-btn');
        const clearBtn = document.getElementById('studio-clear-btn');
        const isCustomLlm = provider === 'custom_llm';
        const isConfigured = isCustomLlm 
            ? Boolean(currentSettings.custom_llm_model && currentSettings.custom_llm_base_url)
            : Boolean(currentSettings[`${provider}_api_key_configured`]);
        const hasKeyConfigured = Boolean(currentSettings[`${provider}_api_key_configured`]);

        if (keyInput) {
            if (hasKeyConfigured && !isEditingKey) {
                // LOCKED state (applies to ANY provider with a securely saved API key)
                keyInput.disabled = true;
                keyInput.classList.add('is-locked');
                keyInput.value = window.ATM.i18n ? window.ATM.i18n.t('plugins.key_locked_value') : '••••••••••••••••••••••••••••••••';
                keyInput.placeholder = '';
                keyInput.title = window.ATM.i18n ? window.ATM.i18n.t('plugins.key_locked_desc') : 'API Key is securely saved';
                if (changeKeyBtn) {
                    changeKeyBtn.classList.remove('hidden');
                    changeKeyBtn.disabled = isStudioBusy;
                    const span = changeKeyBtn.querySelector('span') || changeKeyBtn;
                    span.textContent = window.ATM.i18n ? window.ATM.i18n.t('plugins.change_key') : 'Change Key';
                }
                if (saveBtn) saveBtn.classList.remove('hidden');
                if (clearBtn) {
                    clearBtn.classList.remove('hidden');
                    clearBtn.disabled = isStudioBusy;
                }
            } else {
                // UNLOCKED / EDITING state
                keyInput.disabled = isStudioBusy;
                keyInput.classList.remove('is-locked');
                if (!isEditingKey) {
                    keyInput.value = '';
                }
                keyInput.title = '';
                keyInput.placeholder = meta.keyPlaceholder || (window.ATM.i18n ? window.ATM.i18n.t('plugins.api_key_placeholder') : 'Enter API Key...');
                if (hasKeyConfigured && isEditingKey) {
                    if (changeKeyBtn) {
                        changeKeyBtn.classList.remove('hidden');
                        changeKeyBtn.disabled = isStudioBusy;
                        const span = changeKeyBtn.querySelector('span') || changeKeyBtn;
                        span.textContent = window.ATM.i18n ? window.ATM.i18n.t('plugins.cancel_change_key') : 'Cancel';
                    }
                    if (saveBtn) saveBtn.classList.remove('hidden');
                    if (clearBtn) {
                        clearBtn.classList.remove('hidden');
                        clearBtn.disabled = isStudioBusy;
                    }
                } else {
                    if (changeKeyBtn) {
                        changeKeyBtn.classList.add('hidden');
                        changeKeyBtn.disabled = isStudioBusy;
                    }
                    if (saveBtn) saveBtn.classList.remove('hidden');
                    if (clearBtn) {
                        if (isConfigured) {
                            clearBtn.classList.remove('hidden');
                            clearBtn.disabled = isStudioBusy;
                        } else {
                            clearBtn.classList.add('hidden');
                        }
                    }
                }
            }
        }

        if (statusBadge) {
            const isCustomLlm = provider === 'custom_llm';
            const isReady = isCustomLlm 
                ? Boolean(currentSettings.custom_llm_model && currentSettings.custom_llm_base_url)
                : isConfigured;

            if (isReady) {
                statusBadge.className = 'badge configured';
                statusBadge.textContent = window.ATM.i18n ? window.ATM.i18n.t('plugins.key_configured') : 'Configured';
            } else {
                statusBadge.className = 'badge not-configured';
                statusBadge.textContent = window.ATM.i18n ? window.ATM.i18n.t('plugins.key_not_configured') : 'Key Not Set';
            }
        }

        // Reset warning and test result
        const warnBox = document.getElementById('studio-key-warning');
        if (warnBox) warnBox.style.display = 'none';

        checkModelWarning(provider, currentSettings[`${provider}_model`] || meta.defaultModel);
        resetTestResult();
        renderActiveChips();
    };

    const handleFetchModels = async () => {
        if (isStudioBusy) {
            if (window.ATM.Toast) {
                window.ATM.Toast.show(window.ATM.i18n ? window.ATM.i18n.t('plugins.operation_in_progress') : 'Operation in progress, please wait...', 'warning');
            }
            return;
        }

        const btn = document.getElementById('studio-fetch-models-btn');
        if (!btn) return;

        const opProvider = currentProvider;
        const keyInput = document.getElementById('studio-api-key');
        const urlInput = document.getElementById('studio-base-url');

        const typedKey = keyInput && !keyInput.disabled ? keyInput.value.trim() : '';
        const baseUrl = urlInput ? urlInput.value.trim() : '';
        const isConfigured = opProvider === 'custom_llm'
            ? Boolean(currentSettings.custom_llm_model && currentSettings.custom_llm_base_url)
            : Boolean(currentSettings[`${opProvider}_api_key_configured`]);

        if (!typedKey && !isConfigured && opProvider !== 'custom_llm') {
            const msg = window.ATM.i18n ? window.ATM.i18n.t('error.api_key_missing') : 'API Key is required';
            triggerInputError(keyInput, msg);
            return;
        }

        setStudioBusy(true, 'fetch', opProvider);

        const origChildren = Array.from(btn.childNodes).map(n => n.cloneNode(true));
        btn.textContent = '';
        const spinner = document.createElement('span');
        spinner.className = 'spinner';
        spinner.style.cssText = 'display:inline-block;width:11px;height:11px;border:2px solid currentColor;border-top-color:transparent;border-radius:50%;animation:spin 0.8s linear infinite;margin-right:5px;';
        const txtSpan = document.createElement('span');
        txtSpan.textContent = window.ATM.i18n ? window.ATM.i18n.t('plugins.fetch_models_loading') : 'Loading...';
        btn.appendChild(spinner);
        btn.appendChild(txtSpan);

        try {
            const res = await window.ATM.api.post('ai/models', {
                provider: opProvider,
                api_key: typedKey || undefined,
                base_url: baseUrl || undefined
            });

            if (res && res.status === 'success' && Array.isArray(res.models)) {
                if (res.models.length === 0) {
                    const emptyMsg = window.ATM.i18n ? window.ATM.i18n.t('plugins.fetch_models_empty') : 'No models found for this account.';
                    if (window.ATM.Toast) window.ATM.Toast.show(emptyMsg, 'info');
                } else {
                    if (PROVIDER_METADATA[opProvider]) {
                        PROVIDER_METADATA[opProvider].models = res.models;
                    }

                    // Only touch DOM if user is still on the same provider tab
                    if (currentProvider === opProvider) {
                        const datalist = document.getElementById('studio-models-list');
                        if (datalist) {
                            datalist.replaceChildren();
                            res.models.forEach(m => {
                                const opt = document.createElement('option');
                                opt.value = m;
                                datalist.appendChild(opt);
                            });
                        }

                        const pillsContainer = document.getElementById('studio-model-pills');
                        const modelInput = document.getElementById('studio-model');
                        if (pillsContainer) {
                            pillsContainer.replaceChildren();
                            res.models.slice(0, 8).forEach(m => {
                                const pill = document.createElement('button');
                                pill.type = 'button';
                                pill.className = 'model-pill';
                                pill.textContent = m;
                                pill.addEventListener('click', async () => {
                                    if (isStudioBusy) {
                                        if (window.ATM.Toast) {
                                            window.ATM.Toast.show(window.ATM.i18n ? window.ATM.i18n.t('plugins.operation_in_progress') : 'Operation in progress, please wait...', 'warning');
                                        }
                                        return;
                                    }
                                    if (modelInput) {
                                        modelInput.value = m;
                                        currentSettings[`${currentProvider}_model`] = m;
                                        checkModelWarning(currentProvider, m);
                                        const isCustom = currentProvider === 'custom_llm';
                                        const isConf = isCustom
                                            ? Boolean(currentSettings.custom_llm_model && currentSettings.custom_llm_base_url)
                                            : Boolean(currentSettings[`${currentProvider}_api_key_configured`]);
                                        if (isConf) {
                                            await saveStudioConfig();
                                        }
                                    }
                                });
                                pillsContainer.appendChild(pill);
                            });
                        }
                    }

                    const successMsg = window.ATM.i18n 
                        ? window.ATM.i18n.t('plugins.fetch_models_success', { count: res.models.length })
                        : `Loaded ${res.models.length} available models from your account!`;
                    if (window.ATM.Toast) window.ATM.Toast.show(successMsg, 'success');
                }
            } else {
                const errMsg = (res && res.error) || (window.ATM.i18n ? window.ATM.i18n.t((res && res.code) || 'error.api_connection_failed') : 'Failed to fetch models');
                if (window.ATM.Toast) window.ATM.Toast.show(errMsg, 'error');
            }
        } catch (err) {
            const errMsg = err.message || 'Network error';
            if (window.ATM.Toast) window.ATM.Toast.show(errMsg, 'error');
        } finally {
            btn.replaceChildren(...origChildren);
            setStudioBusy(false);
        }
    };

    const saveStudioConfig = async (providerToSave, isInternal = false) => {
        const targetProvider = providerToSave || currentProvider;
        if (isStudioBusy && !isInternal) {
            if (window.ATM.Toast) {
                window.ATM.Toast.show(window.ATM.i18n ? window.ATM.i18n.t('plugins.operation_in_progress') : 'Operation in progress, please wait...', 'warning');
            }
            return;
        }

        const isCurrent = targetProvider === currentProvider;
        const keyInput = document.getElementById('studio-api-key');
        const modelInput = document.getElementById('studio-model');
        const urlInput = document.getElementById('studio-base-url');

        const typedKey = (isCurrent && keyInput && !keyInput.disabled) ? keyInput.value.trim() : '';
        let model = (isCurrent && modelInput) ? modelInput.value.trim() : (currentSettings[`${targetProvider}_model`] || '');
        const baseUrl = (isCurrent && urlInput) ? urlInput.value.trim() : (currentSettings[`${targetProvider}_base_url`] || '');
        const isConfigured = targetProvider === 'custom_llm'
            ? Boolean(currentSettings.custom_llm_model && currentSettings.custom_llm_base_url)
            : Boolean(currentSettings[`${targetProvider}_api_key_configured`]);

        if (isCurrent) {
            // Auto-resolve fuzzy model suggestion if user typed colloquial name or characters like space/comma
            const suggestion = suggestModelName(targetProvider, model);
            if (suggestion && (suggestion !== model.toLowerCase() && (/[,\s]/.test(model) || model.length < 6))) {
                model = suggestion;
                if (modelInput) modelInput.value = suggestion;
                checkModelWarning(targetProvider, suggestion);
            } else if (/[,\s]/.test(model)) {
                const msg = window.ATM.i18n ? window.ATM.i18n.t('plugins.invalid_model_chars') : 'Model name cannot contain spaces or commas.';
                triggerInputError(modelInput, msg);
                return;
            }

            // Auto-normalize model casing for official cloud providers
            if (['gemini', 'openai', 'deepseek', 'claude', 'kimi'].includes(targetProvider)) {
                model = model.toLowerCase();
                if (modelInput) modelInput.value = model;
            }

            // Validate model name presence
            if (!model) {
                const msg = window.ATM.i18n ? window.ATM.i18n.t('error.model_missing') : 'Please select or enter an AI Model name.';
                triggerInputError(modelInput, msg);
                return;
            }

            // Validate cross-provider model mismatch
            const modelMismatch = detectModelMismatch(targetProvider, model);
            if (modelMismatch) {
                triggerInputError(modelInput, modelMismatch.warning);
                checkModelWarning(targetProvider, model);
                return;
            }
        }

        let keyWarning = null;
        if (typedKey) {
            const check = validateKeyFormat(targetProvider, typedKey);
            if (!check.valid) {
                if (isCurrent) triggerInputError(keyInput, check.message);
                return;
            }
            if (check.warning) {
                keyWarning = check.warning;
            }
        } else if (!isConfigured && targetProvider !== 'custom_llm') {
            const msg = window.ATM.i18n ? window.ATM.i18n.t('error.api_key_missing') : 'API Key is required';
            if (isCurrent) triggerInputError(keyInput, msg);
            return;
        }

        const payload = {};
        if (targetProvider === 'custom_llm') {
            if (typedKey) payload.custom_llm_api_key = typedKey;
            if (model) payload.custom_llm_model = model;
            if (baseUrl) payload.custom_llm_base_url = baseUrl;
        } else {
            if (typedKey) payload[`${targetProvider}_api_key`] = typedKey;
            if (model) payload[`${targetProvider}_model`] = model;
            if (baseUrl) payload[`${targetProvider}_base_url`] = baseUrl;
        }

        if (Object.keys(payload).length === 0 && !typedKey) return;

        if (!isInternal) {
            const savingMsg = window.ATM.i18n ? window.ATM.i18n.t('plugins.saving_in_progress') : 'Saving configuration...';
            setStudioBusy(true, 'save', targetProvider, savingMsg);
        }

        try {
            const res = await window.ATM.api.post('settings', payload);
            if (res && res.status === 'error') {
                if (isCurrent) triggerInputError(keyInput, res.error || 'Failed to save');
                return;
            }

            if (targetProvider === 'custom_llm') {
                if (typedKey) {
                    currentSettings.custom_llm_api_key = typedKey;
                    currentSettings.custom_llm_api_key_configured = true;
                }
                if (model) currentSettings.custom_llm_model = model;
                if (baseUrl) currentSettings.custom_llm_base_url = baseUrl;
                currentSettings.custom_llm_configured = Boolean(model && baseUrl);
            } else {
                if (typedKey) currentSettings[`${targetProvider}_api_key_configured`] = true;
                if (model) currentSettings[`${targetProvider}_model`] = model;
                if (baseUrl) currentSettings[`${targetProvider}_base_url`] = baseUrl;
            }

            isEditingKey = false;

            if (window.ATM.Toast) {
                const msg = window.ATM.i18n ? window.ATM.i18n.t('plugins.key_saved') : 'Configuration saved';
                const warn = keyWarning || (res && res.warning);
                if (warn) {
                    window.ATM.Toast.show(`${msg} (${warn})`, 'warning');
                } else {
                    window.ATM.Toast.show(msg, 'success');
                }
            }

            if (window.ATM.events) {
                window.ATM.events.publish('settings:updated', currentSettings);
            }
        } catch (err) {
            if (isCurrent) {
                triggerInputError(keyInput, err.message || (window.ATM.i18n ? window.ATM.i18n.t('toast.settings_error') : 'Failed to save'));
            } else if (window.ATM.Toast) {
                window.ATM.Toast.show(err.message || 'Failed to save', 'error');
            }
        } finally {
            if (!isInternal) {
                setStudioBusy(false);
            }
        }
    };

    const clearStudioConfig = async (providerToClear) => {
        const targetProvider = providerToClear || currentProvider;
        if (isStudioBusy) {
            if (window.ATM.Toast) {
                window.ATM.Toast.show(window.ATM.i18n ? window.ATM.i18n.t('plugins.operation_in_progress') : 'Operation in progress, please wait...', 'warning');
            }
            return;
        }

        const meta = PROVIDER_METADATA[targetProvider] || { name: targetProvider, defaultModel: '', defaultUrl: '' };
        const confirmMsg = window.ATM.i18n 
            ? window.ATM.i18n.t('plugins.clear_key_confirm', { provider: meta.name }) 
            : `Are you sure you want to remove the API Key and configuration for ${meta.name}?`;

        let agreed = false;
        if (window.ATM.Modals && typeof window.ATM.Modals.confirm === 'function') {
            agreed = await window.ATM.Modals.confirm(confirmMsg);
        } else {
            agreed = window.confirm(confirmMsg);
        }
        if (!agreed) {
            return;
        }

        const clearingMsg = window.ATM.i18n ? window.ATM.i18n.t('plugins.clearing_in_progress') : 'Clearing configuration...';
        setStudioBusy(true, 'clear', targetProvider, clearingMsg);

        try {
            const payload = {};
            if (targetProvider === 'custom_llm') {
                payload.custom_llm_api_key = '';
                payload.custom_llm_model = '';
                payload.custom_llm_base_url = '';

                currentSettings.custom_llm_api_key = '';
                currentSettings.custom_llm_model = '';
                currentSettings.custom_llm_base_url = '';
                currentSettings.custom_llm_api_key_configured = false;
                currentSettings.custom_llm_configured = false;
            } else {
                payload[`${targetProvider}_api_key`] = '';
                payload[`${targetProvider}_model`] = meta.defaultModel;
                payload[`${targetProvider}_base_url`] = meta.defaultUrl;

                currentSettings[`${targetProvider}_api_key_configured`] = false;
                currentSettings[`${targetProvider}_model`] = meta.defaultModel;
                currentSettings[`${targetProvider}_base_url`] = meta.defaultUrl;
            }

            await window.ATM.api.post('settings', payload);

            isEditingKey = false;

            if (window.ATM.Toast) {
                const msg = window.ATM.i18n 
                    ? window.ATM.i18n.t('plugins.clear_key_success', { provider: meta.name }) 
                    : `API Key and configuration for ${meta.name} removed successfully.`;
                window.ATM.Toast.show(msg, 'info');
            }

            if (window.ATM.events) {
                window.ATM.events.publish('settings:updated', currentSettings);
            }
        } catch (err) {
            if (window.ATM.Toast) {
                const msg = window.ATM.i18n ? window.ATM.i18n.t('toast.settings_error') : 'Failed to clear key';
                window.ATM.Toast.show(msg, 'error');
            }
        } finally {
            setStudioBusy(false);
        }
    };

    const handleResetModel = async () => {
        if (isStudioBusy) {
            if (window.ATM.Toast) {
                window.ATM.Toast.show(window.ATM.i18n ? window.ATM.i18n.t('plugins.operation_in_progress') : 'Operation in progress, please wait...', 'warning');
            }
            return;
        }

        const meta = PROVIDER_METADATA[currentProvider] || PROVIDER_METADATA.gemini;
        const defaultModel = meta.defaultModel;
        const modelInput = document.getElementById('studio-model');
        if (modelInput) {
            modelInput.value = defaultModel;
        }
        currentSettings[`${currentProvider}_model`] = defaultModel;
        checkModelWarning(currentProvider, defaultModel);

        const isCustomLlm = currentProvider === 'custom_llm';
        const isConfigured = isCustomLlm
            ? Boolean(currentSettings.custom_llm_model && currentSettings.custom_llm_base_url)
            : Boolean(currentSettings[`${currentProvider}_api_key_configured`]);

        if (isConfigured) {
            await saveStudioConfig();
        }

        if (window.ATM.Toast) {
            const successMsg = window.ATM.i18n 
                ? window.ATM.i18n.t('plugins.reset_model_success', { model: defaultModel, provider: meta.name })
                : `Reset to default model (${defaultModel}) for ${meta.name}.`;
            window.ATM.Toast.show(successMsg, 'info');
        }
    };

    const handleStudioTest = async () => {
        if (isStudioBusy) {
            if (window.ATM.Toast) {
                window.ATM.Toast.show(window.ATM.i18n ? window.ATM.i18n.t('plugins.operation_in_progress') : 'Operation in progress, please wait...', 'warning');
            }
            return;
        }

        const btn = document.getElementById('studio-test-btn');
        if (!btn) return;

        const opProvider = currentProvider;
        const keyInput = document.getElementById('studio-api-key');
        const modelInput = document.getElementById('studio-model');
        const urlInput = document.getElementById('studio-base-url');
        const resultSpan = document.getElementById('studio-test-result');

        const typedKey = keyInput && !keyInput.disabled ? keyInput.value.trim() : '';
        let model = modelInput ? modelInput.value.trim() : '';
        const baseUrl = urlInput ? urlInput.value.trim() : '';
        const isConfigured = opProvider === 'custom_llm'
            ? Boolean(currentSettings.custom_llm_model && currentSettings.custom_llm_base_url)
            : Boolean(currentSettings[`${opProvider}_api_key_configured`]);

        // Auto-resolve fuzzy model suggestion if user typed colloquial name or characters like space/comma
        const suggestion = suggestModelName(opProvider, model);
        if (suggestion && (suggestion !== model.toLowerCase() && (/[,\s]/.test(model) || model.length < 6))) {
            model = suggestion;
            if (modelInput) modelInput.value = suggestion;
            checkModelWarning(opProvider, suggestion);
        } else if (/[,\s]/.test(model)) {
            const msg = window.ATM.i18n ? window.ATM.i18n.t('plugins.invalid_model_chars') : 'Model name cannot contain spaces or commas.';
            triggerInputError(modelInput, msg);
            if (resultSpan) {
                resultSpan.className = 'test-latency error';
                resultSpan.textContent = `✗ ${msg}`;
            }
            if (testResultTimeout) clearTimeout(testResultTimeout);
            testResultTimeout = setTimeout(resetTestResult, 5000);
            return;
        }

        // Auto-normalize model casing for official cloud providers
        if (['gemini', 'openai', 'deepseek', 'claude', 'kimi'].includes(opProvider)) {
            model = model.toLowerCase();
            if (modelInput) modelInput.value = model;
        }

        // Key presence check
        if (!typedKey && !isConfigured && opProvider !== 'custom_llm') {
            const msg = window.ATM.i18n ? window.ATM.i18n.t('error.api_key_missing') : 'API Key is required';
            triggerInputError(keyInput, msg);
            if (resultSpan) {
                resultSpan.className = 'test-latency error';
                resultSpan.textContent = `✗ ${msg}`;
            }
            if (testResultTimeout) clearTimeout(testResultTimeout);
            testResultTimeout = setTimeout(resetTestResult, 5000);
            return;
        }

        // Custom LLM URL presence check
        if (opProvider === 'custom_llm') {
            const urlVal = urlInput ? urlInput.value.trim() : '';
            if (!urlVal && !currentSettings.custom_llm_base_url) {
                const msg = window.ATM.i18n ? window.ATM.i18n.t('error.base_url_missing') : 'Base URL is required for Custom / Local LLM';
                triggerInputError(urlInput, msg);
                if (resultSpan) {
                    resultSpan.className = 'test-latency error';
                    resultSpan.textContent = `✗ ${msg}`;
                }
                if (testResultTimeout) clearTimeout(testResultTimeout);
                testResultTimeout = setTimeout(resetTestResult, 5000);
                return;
            }
        }

        // Model presence check
        if (!model) {
            const msg = window.ATM.i18n ? window.ATM.i18n.t('error.model_missing') : 'Please select or enter an AI Model name.';
            triggerInputError(modelInput, msg);
            if (resultSpan) {
                resultSpan.className = 'test-latency error';
                resultSpan.textContent = `✗ ${msg}`;
            }
            if (testResultTimeout) clearTimeout(testResultTimeout);
            testResultTimeout = setTimeout(resetTestResult, 5000);
            return;
        }

        // Cross-provider model mismatch check
        const modelMismatch = detectModelMismatch(opProvider, model);
        if (modelMismatch) {
            triggerInputError(modelInput, modelMismatch.warning);
            checkModelWarning(opProvider, model);
            if (resultSpan) {
                resultSpan.className = 'test-latency error';
                resultSpan.textContent = `✗ ${modelMismatch.warning}`;
            }
            if (testResultTimeout) clearTimeout(testResultTimeout);
            testResultTimeout = setTimeout(resetTestResult, 5000);
            return;
        }

        // Format validation if typed
        if (typedKey) {
            const check = validateKeyFormat(opProvider, typedKey);
            if (!check.valid) {
                triggerInputError(keyInput, check.message);
                if (resultSpan) {
                    resultSpan.className = 'test-latency error';
                    resultSpan.textContent = `✗ ${check.message}`;
                }
                if (testResultTimeout) clearTimeout(testResultTimeout);
                testResultTimeout = setTimeout(resetTestResult, 5000);
                return;
            }
        }

        setStudioBusy(true, 'test', opProvider);

        const origChildren = Array.from(btn.childNodes).map(n => n.cloneNode(true));
        btn.textContent = '';
        const spinner = document.createElement('span');
        spinner.className = 'spinner';
        spinner.style.cssText = 'display:inline-block;width:12px;height:12px;border:2px solid currentColor;border-top-color:transparent;border-radius:50%;animation:spin 0.8s linear infinite;margin-right:6px;';
        const txtSpan = document.createElement('span');
        txtSpan.textContent = window.ATM.i18n ? window.ATM.i18n.t('plugins.testing') : 'Testing...';
        btn.appendChild(spinner);
        btn.appendChild(txtSpan);

        resetTestResult();

        try {
            const res = await window.ATM.api.post('ai/test-connection', {
                provider: opProvider,
                api_key: typedKey || undefined,
                model: model || undefined,
                base_url: baseUrl || undefined
            });

            if (res.status === 'success') {
                let successMsg = window.ATM.i18n 
                    ? window.ATM.i18n.t('plugins.test_success', { ms: res.latency_ms })
                    : `Connection successful (${res.latency_ms}ms)!`;
                if (res.warning) {
                    successMsg += ` (${res.warning})`;
                }

                if (currentProvider === opProvider && resultSpan) {
                    resultSpan.className = res.warning ? 'test-latency warning' : 'test-latency success';
                    resultSpan.textContent = `✓ ${successMsg}`;
                }
                if (window.ATM.Toast) {
                    window.ATM.Toast.show(successMsg, res.warning ? 'warning' : 'success');
                }

                if (typedKey || model || baseUrl) {
                    await saveStudioConfig(opProvider, true);
                }
            } else {
                const errMsg = res.error || (window.ATM.i18n ? window.ATM.i18n.t(res.code || 'error.api_connection_failed') : 'Connection failed');
                const fullMsg = window.ATM.i18n 
                    ? window.ATM.i18n.t('plugins.test_failed', { error: errMsg })
                    : `Connection failed: ${errMsg}`;
                if (currentProvider === opProvider && resultSpan) {
                    resultSpan.className = 'test-latency error';
                    resultSpan.textContent = `✗ ${errMsg}`;
                }
                if (window.ATM.Toast) {
                    window.ATM.Toast.show(fullMsg, 'error');
                }
            }
        } catch (err) {
            const errMsg = err.message || 'Network error';
            const fullMsg = window.ATM.i18n 
                ? window.ATM.i18n.t('plugins.test_failed', { error: errMsg })
                : `Connection failed: ${errMsg}`;
            if (currentProvider === opProvider && resultSpan) {
                resultSpan.className = 'test-latency error';
                resultSpan.textContent = `✗ ${errMsg}`;
            }
            if (window.ATM.Toast) {
                window.ATM.Toast.show(fullMsg, 'error');
            }
        } finally {
            btn.replaceChildren(...origChildren);
            setStudioBusy(false);
            if (testResultTimeout) clearTimeout(testResultTimeout);
            testResultTimeout = setTimeout(resetTestResult, 5000);
        }
    };

    const saveDeeplConfig = async () => {
        const keyInput = document.getElementById('deepl-api-key');
        if (!keyInput || !keyInput.value.trim()) return;
        const key = keyInput.value.trim();

        if (key.length < 20) {
            const msg = window.ATM.i18n ? window.ATM.i18n.t('error.key_too_short_deepl') : 'DeepL API key is too short (min 20 chars)';
            triggerInputError(keyInput, msg);
            return;
        }

        try {
            await window.ATM.api.post('settings', { deepl_api_key: key });
            currentSettings.deepl_api_key_configured = true;
            keyInput.value = '';
            keyInput.placeholder = window.ATM.i18n ? window.ATM.i18n.t('plugins.key_configured') : 'Configured';
            const badge = document.getElementById('deepl-status-badge');
            if (badge) {
                badge.className = 'badge configured';
                badge.textContent = window.ATM.i18n ? window.ATM.i18n.t('plugins.key_configured') : 'Configured';
            }
            const clearBtn = document.getElementById('deepl-clear-btn');
            if (clearBtn) clearBtn.classList.remove('hidden');

            if (window.ATM.Toast) {
                window.ATM.Toast.show(window.ATM.i18n ? window.ATM.i18n.t('plugins.key_saved') : 'Configuration saved', 'success');
            }

            if (window.ATM.events) {
                window.ATM.events.publish('settings:updated', currentSettings);
            }
        } catch (e) {
            triggerInputError(keyInput, window.ATM.i18n ? window.ATM.i18n.t('toast.settings_error') : 'Failed to save');
        }
    };

    const clearDeeplConfig = async () => {
        const confirmMsg = window.ATM.i18n 
            ? window.ATM.i18n.t('plugins.clear_key_confirm', { provider: 'DeepL' }) 
            : 'Are you sure you want to remove the API Key and configuration for DeepL?';

        let agreed = false;
        if (window.ATM.Modals && typeof window.ATM.Modals.confirm === 'function') {
            agreed = await window.ATM.Modals.confirm(confirmMsg);
        } else {
            agreed = window.confirm(confirmMsg);
        }
        if (!agreed) {
            return;
        }

        try {
            await window.ATM.api.post('settings', { deepl_api_key: '' });
            currentSettings.deepl_api_key_configured = false;
            const keyInput = document.getElementById('deepl-api-key');
            if (keyInput) {
                keyInput.value = '';
                keyInput.placeholder = window.ATM.i18n ? window.ATM.i18n.t('plugins.deepl_placeholder') : 'Enter DeepL Auth Key...';
            }
            const badge = document.getElementById('deepl-status-badge');
            if (badge) {
                badge.className = 'badge not-configured';
                badge.textContent = window.ATM.i18n ? window.ATM.i18n.t('plugins.key_not_configured') : 'Key Not Set';
            }
            const clearBtn = document.getElementById('deepl-clear-btn');
            if (clearBtn) clearBtn.classList.add('hidden');

            if (window.ATM.Toast) {
                const msg = window.ATM.i18n 
                    ? window.ATM.i18n.t('plugins.clear_key_success', { provider: 'DeepL' }) 
                    : 'API Key and configuration for DeepL removed successfully.';
                window.ATM.Toast.show(msg, 'info');
            }

            if (window.ATM.events) {
                window.ATM.events.publish('settings:updated', currentSettings);
            }
        } catch (e) {
            if (window.ATM.Toast) {
                window.ATM.Toast.show(window.ATM.i18n ? window.ATM.i18n.t('toast.settings_error') : 'Failed to clear key', 'error');
            }
        }
    };

    return {
        init: () => {
            const tmEl = document.getElementById('tm-threshold');
            const langSel = document.getElementById('ui-lang-select');

            const saveSettings = () => {
                const themeToggle = document.getElementById('theme-toggle');
                const isDark = themeToggle ? themeToggle.checked : true;
                const payload = {
                    dark_mode: isDark,
                    translation_memory_threshold: tmEl ? Number(tmEl.value) : 0.85,
                    ui_language: langSel ? langSel.value : 'vi'
                };

                window.ATM.api.post('settings', payload).then(() => {
                    if (langSel && langSel.value !== window.ATM.i18n.getLang()) {
                        window.ATM.i18n.setLang(langSel.value);
                    }
                    if (window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n.t('toast.settings_saved') || '');
                }).catch(() => {
                    if (window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n.t('toast.settings_error') || '', true);
                });
            };

            if (tmEl) tmEl.addEventListener('change', saveSettings);
            if (langSel) langSel.addEventListener('change', saveSettings);

            // Studio Tabs
            const tabsContainer = document.getElementById('studio-provider-tabs');
            if (tabsContainer) {
                tabsContainer.querySelectorAll('.studio-tab').forEach(tab => {
                    tab.addEventListener('click', () => {
                        if (isStudioBusy) {
                            if (window.ATM.Toast) {
                                window.ATM.Toast.show(window.ATM.i18n ? window.ATM.i18n.t('plugins.operation_in_progress') : 'Operation in progress, please wait...', 'warning');
                            }
                            return;
                        }
                        const prov = tab.dataset.provider;
                        if (prov) {
                            isEditingKey = false;
                            renderProviderContext(prov);
                        }
                    });
                });
            }

            // Studio Change Key Button
            const changeKeyBtn = document.getElementById('studio-change-key-btn');
            if (changeKeyBtn) {
                changeKeyBtn.addEventListener('click', () => {
                    if (isStudioBusy) {
                        if (window.ATM.Toast) {
                            window.ATM.Toast.show(window.ATM.i18n ? window.ATM.i18n.t('plugins.operation_in_progress') : 'Operation in progress, please wait...', 'warning');
                        }
                        return;
                    }
                    isEditingKey = !isEditingKey;
                    renderProviderContext(currentProvider);
                    if (isEditingKey) {
                        const input = document.getElementById('studio-api-key');
                        if (input) {
                            input.value = '';
                            input.focus();
                        }
                    }
                });
            }

            // Studio Provider Select dropdown (if present)
            const studioSel = document.getElementById('studio-provider-select');
            if (studioSel) {
                studioSel.addEventListener('change', (e) => {
                    if (isStudioBusy) {
                        if (window.ATM.Toast) {
                            window.ATM.Toast.show(window.ATM.i18n ? window.ATM.i18n.t('plugins.operation_in_progress') : 'Operation in progress, please wait...', 'warning');
                        }
                        e.target.value = currentProvider;
                        return;
                    }
                    isEditingKey = false;
                    renderProviderContext(e.target.value);
                });
            }

            // Studio Model Reset Button
            const resetModelBtn = document.getElementById('studio-reset-model-btn');
            if (resetModelBtn) {
                resetModelBtn.addEventListener('click', handleResetModel);
            }

            // Studio Model input - Model Mismatch Detection & Real-time Draft Sync
            const studioModelInput = document.getElementById('studio-model');
            if (studioModelInput) {
                studioModelInput.addEventListener('input', (e) => {
                    if (currentProvider) currentSettings[`${currentProvider}_model`] = e.target.value.trim();
                    checkModelWarning(currentProvider, e.target.value);
                });
                studioModelInput.addEventListener('change', (e) => {
                    if (currentProvider) currentSettings[`${currentProvider}_model`] = e.target.value.trim();
                });
            }

            // Studio Base URL input - Real-time Draft Sync
            const studioBaseUrlInput = document.getElementById('studio-base-url');
            if (studioBaseUrlInput) {
                studioBaseUrlInput.addEventListener('input', (e) => {
                    if (currentProvider) currentSettings[`${currentProvider}_base_url`] = e.target.value.trim();
                });
                studioBaseUrlInput.addEventListener('change', (e) => {
                    if (currentProvider) currentSettings[`${currentProvider}_base_url`] = e.target.value.trim();
                });
            }

            // Studio API Key input - Smart Key Detection & Timer Reset
            const studioKeyInput = document.getElementById('studio-api-key');
            if (studioKeyInput) {
                studioKeyInput.addEventListener('input', (e) => {
                    resetTestResult();
                    const warnBox = document.getElementById('studio-key-warning');
                    const warnText = document.getElementById('studio-warning-text');
                    const warnMsg = detectKeyFormatWarning(currentProvider, e.target.value);
                    if (warnMsg && warnBox && warnText) {
                        warnText.textContent = warnMsg;
                        warnBox.style.display = 'flex';
                    } else if (warnBox) {
                        warnBox.style.display = 'none';
                    }
                });
            }

            // Studio Actions: Fetch Models, Save, Clear, Test
            const fetchModelsBtn = document.getElementById('studio-fetch-models-btn');
            if (fetchModelsBtn) {
                fetchModelsBtn.addEventListener('click', handleFetchModels);
            }

            const saveBtn = document.getElementById('studio-save-btn');
            if (saveBtn) {
                saveBtn.addEventListener('click', () => saveStudioConfig());
            }

            const clearBtn = document.getElementById('studio-clear-btn');
            if (clearBtn) {
                clearBtn.addEventListener('click', () => clearStudioConfig());
            }

            const testBtn = document.getElementById('studio-test-btn');
            if (testBtn) {
                testBtn.addEventListener('click', handleStudioTest);
            }

            // DeepL API Card
            const deeplKeyInput = document.getElementById('deepl-api-key');
            if (deeplKeyInput) {
                deeplKeyInput.addEventListener('change', saveDeeplConfig);
            }

            const deeplClearBtn = document.getElementById('deepl-clear-btn');
            if (deeplClearBtn) {
                deeplClearBtn.addEventListener('click', clearDeeplConfig);
            }

            // Eye visibility toggling for API keys
            document.querySelectorAll('.btn-toggle-eye').forEach(btn => {
                btn.addEventListener('click', () => {
                    const targetId = btn.dataset.target;
                    const input = document.getElementById(targetId);
                    if (!input) return;
                    if (input.type === 'password') {
                        input.type = 'text';
                        btn.classList.add('is-visible');
                        btn.classList.add('active');
                    } else {
                        input.type = 'password';
                        btn.classList.remove('is-visible');
                        btn.classList.remove('active');
                    }
                });
            });

            // Accent color picker
            const picker = document.getElementById('accent-color-picker');
            const resetBtn = document.getElementById('accent-reset-btn');
            
            const applyAccent = (hex) => {
                if (!hex) return;
                document.documentElement.style.setProperty('--accent', hex);
                const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
                if (m) {
                    const r = parseInt(m[1], 16), g = parseInt(m[2], 16), b = parseInt(m[3], 16);
                    document.documentElement.style.setProperty('--accent-rgb', `${r}, ${g}, ${b}`);
                }
                localStorage.setItem('atm_accent', hex);
            };

            if (picker) {
                picker.addEventListener('input', (e) => applyAccent(e.target.value));
            }
            if (resetBtn) {
                resetBtn.addEventListener('click', () => {
                    const DEFAULT_ACCENT = '#7000ff';
                    if (picker) picker.value = DEFAULT_ACCENT;
                    applyAccent(DEFAULT_ACCENT);
                });
            }

            if (window.ATM.events) {
                window.ATM.events.subscribe('lang:changed', () => {
                    renderProviderContext(currentProvider);
                    renderActiveChips();
                    const isDeepl = Boolean(currentSettings.deepl_api_key_configured);
                    const deeplBadge = document.getElementById('deepl-status-badge');
                    if (deeplBadge) {
                        deeplBadge.textContent = window.ATM.i18n ? window.ATM.i18n.t(isDeepl ? 'plugins.key_configured' : 'plugins.key_not_configured') : (isDeepl ? 'Configured' : 'Key Not Set');
                    }
                });
            }
        },
        
        load: async () => {
            try {
                const s = await window.ATM.api.get('settings');
                currentSettings = s || {};
                
                const toggle = document.getElementById('theme-toggle');
                if (toggle) {
                    toggle.checked = currentSettings.dark_mode !== false;
                    if (window.ATM.Theme && window.ATM.Theme.applyTheme) {
                        window.ATM.Theme.applyTheme(toggle.checked);
                    }
                    const localSettings = window.ATM.store.get('atm_settings', {});
                    localSettings.dark_mode = toggle.checked;
                    window.ATM.store.set('atm_settings', localSettings);
                }

                if (currentSettings.ui_language && currentSettings.ui_language !== window.ATM.i18n.getLang()) {
                    window.ATM.i18n.setLang(currentSettings.ui_language);
                }
                const langSel = document.getElementById('ui-lang-select');
                if (langSel) langSel.value = currentSettings.ui_language || 'vi';

                const tmEl = document.getElementById('tm-threshold');
                if (tmEl) tmEl.value = currentSettings.translation_memory_threshold != null ? currentSettings.translation_memory_threshold : 0.85;

                const savedAccent = localStorage.getItem('atm_accent');
                if (savedAccent) {
                    const picker = document.getElementById('accent-color-picker');
                    if (picker) picker.value = savedAccent;
                }

                // Render Universal Studio for current provider
                renderProviderContext(currentProvider);

                // DeepL API Card State
                const deeplKeyInput = document.getElementById('deepl-api-key');
                const deeplBadge = document.getElementById('deepl-status-badge');
                const deeplClearBtn = document.getElementById('deepl-clear-btn');
                const isDeeplConfigured = Boolean(currentSettings.deepl_api_key_configured);

                if (deeplKeyInput) {
                    deeplKeyInput.value = '';
                    if (isDeeplConfigured) {
                        deeplKeyInput.placeholder = window.ATM.i18n ? window.ATM.i18n.t('plugins.key_configured') : 'Configured';
                    } else {
                        deeplKeyInput.placeholder = window.ATM.i18n ? window.ATM.i18n.t('plugins.deepl_placeholder') : 'Enter DeepL Auth Key...';
                    }
                }

                if (deeplBadge) {
                    if (isDeeplConfigured) {
                        deeplBadge.className = 'badge configured';
                        deeplBadge.textContent = window.ATM.i18n ? window.ATM.i18n.t('plugins.key_configured') : 'Configured';
                    } else {
                        deeplBadge.className = 'badge not-configured';
                        deeplBadge.textContent = window.ATM.i18n ? window.ATM.i18n.t('plugins.key_not_configured') : 'Key Not Set';
                    }
                }

                if (deeplClearBtn) {
                    if (isDeeplConfigured) {
                        deeplClearBtn.classList.remove('hidden');
                    } else {
                        deeplClearBtn.classList.add('hidden');
                    }
                }
            } catch (e) {
                console.error('Failed to load settings:', e);
            }
        }
    };
})();

