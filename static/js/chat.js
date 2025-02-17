// 滚动到指定消息
function scrollToMessage(messageId) {
    const message = document.getElementById(messageId);
    if (message) {
        message.scrollIntoView({ behavior: 'smooth', block: 'center' });
        message.classList.add('highlight');
        setTimeout(() => message.classList.remove('highlight'), 1500);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // 配置marked使用highlight.js
    marked.setOptions({
        highlight: function(code, lang) {
            if (lang && hljs.getLanguage(lang)) {
                return hljs.highlight(code, { language: lang }).value;
            }
            return hljs.highlightAuto(code).value;
        }
    });

    // 获取DOM元素
    const chatMessages = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const historyList = document.getElementById('history-list');
    const studentId = document.getElementById('student-id');
    const studentName = document.getElementById('student-name');
    const logoutBtn = document.getElementById('logout-btn');

    // 请求头部
    const headers = {
        'Content-Type': 'application/json'
    };

    // 格式化时间
    function formatTime(date) {
        return new Date(date).toLocaleString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    // 添加消息到聊天区域
    function addMessage(content, isUser = false, time = new Date()) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
        const renderedContent = isUser ? content : marked.parse(content);
        messageDiv.innerHTML = `
            <div class="message-content">${renderedContent}</div>
            <div class="message-time">${formatTime(time)}</div>
        `;
        chatMessages.appendChild(messageDiv);
        // 初始化新添加内容的代码高亮
        if (!isUser) {
            messageDiv.querySelectorAll('pre code').forEach((block) => {
                hljs.highlightElement(block);
            });
        }
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return messageDiv;
    }

    // 添加加载动画
    function addLoadingIndicator() {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'loading';
        loadingDiv.innerHTML = `
            正在思考
            <div class="dots">
                <div class="dot"></div>
                <div class="dot"></div>
                <div class="dot"></div>
            </div>
        `;
        chatMessages.appendChild(loadingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return loadingDiv;
    }

    // 发送消息
    async function sendMessage() {
        const question = chatInput.value.trim();
        if (!question) return;

        // 禁用输入和发送按钮
        chatInput.disabled = true;
        sendBtn.disabled = true;

        // 显示用户消息
        addMessage(question, true);
        chatInput.value = '';

        // 显示加载动画
        const loadingIndicator = addLoadingIndicator();

        try {
            // 创建消息容器
            const assistantMessage = document.createElement('div');
            assistantMessage.className = 'message assistant';
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            const timeDiv = document.createElement('div');
            timeDiv.className = 'message-time';
            timeDiv.textContent = formatTime(new Date());
            assistantMessage.appendChild(contentDiv);
            assistantMessage.appendChild(timeDiv);

            // 移除加载动画并添加消息容器
            loadingIndicator.remove();
            chatMessages.appendChild(assistantMessage);

            // 发起流式请求
            const response = await fetch('/api/chat/stream', {
                method: 'POST',
                headers,
                body: JSON.stringify({ question })
            });

            if (!response.ok) {
                const data = await response.json();
                if (response.status === 429 || response.status === 403) {
                    throw new Error(data.detail);
                }
                throw new Error('发送消息失败');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let answer = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                
                const text = decoder.decode(value);
                answer += text;
                contentDiv.innerHTML = marked.parse(answer);
                // 初始化新添加内容的代码高亮
                contentDiv.querySelectorAll('pre code').forEach((block) => {
                    hljs.highlightElement(block);
                });
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }

            // 保存问答记录
            const saveResponse = await fetch('/api/chat/save', {
                method: 'POST',
                headers,
                body: JSON.stringify({
                    question,
                    answer
                })
            });

            if (!saveResponse.ok) {
                if (saveResponse.status === 429) {
                    const data = await saveResponse.json();
                    throw new Error(data.detail);
                }
                console.error('保存问答记录失败');
            }

            // 刷新历史记录
            loadHistory();
        } catch (error) {
            console.error('发送消息失败:', error);
            loadingIndicator.remove();
            const errorMessage = error.message.includes('请等待') || error.message.includes('权限已被禁用')
                ? error.message 
                : '抱歉,发送消息失败,请重试';
            addMessage(errorMessage, false);
        } finally {
            // 恢复输入和发送按钮
            chatInput.disabled = false;
            sendBtn.disabled = false;
            chatInput.focus();
        }
    }

    // 格式化日期
    function formatDate(date) {
        return new Date(date).toLocaleDateString('zh-CN');
    }

    // 加载历史记录
    async function loadHistory() {
        try {
            const response = await fetch('/api/chat/history', { headers });
            let data = await response.json();
            
            // 按时间顺序排序
            data.sort((a, b) => new Date(a.chat_time) - new Date(b.chat_time));
            
            // 按日期分组
            const groupedData = data.reduce((groups, chat) => {
                const date = formatDate(chat.chat_time);
                if (!groups[date]) {
                    groups[date] = [];
                }
                groups[date].push(chat);
                return groups;
            }, {});

            // 清空聊天区域,只保留系统欢迎消息
            chatMessages.innerHTML = `
                <div class="system-message">
                    欢迎使用AI问答功能!我是你的Python学习助手,请问有什么可以帮你的吗?
                </div>
            `;

            // 添加历史消息到聊天区域
            Object.entries(groupedData).forEach(([date, chats]) => {
                // 添加日期分割线
                chatMessages.innerHTML += `
                    <div class="date-divider">
                        <span>${date}</span>
                    </div>
                `;

                // 添加该日期下的所有对话
                chats.forEach(chat => {
                    const messageId = `message-${chat.id}`;
                    chatMessages.innerHTML += `
                    <div id="${messageId}" class="message user">
                        <div class="message-content">${chat.question}</div>
                        <div class="message-time">${formatTime(chat.chat_time)}</div>
                    </div>
                    <div class="message assistant">
                        <div class="message-content">${marked.parse(chat.answer)}</div>
                        <div class="message-time">${formatTime(chat.chat_time)}</div>
                    </div>
                    `;
                });

                // 初始化历史消息的代码高亮
                chatMessages.querySelectorAll('pre code').forEach((block) => {
                    hljs.highlightElement(block);
                });
            });

            // 更新右侧历史记录列表(倒序显示)
            historyList.innerHTML = [...data].reverse().map(chat => `
                <div class="history-item" onclick="scrollToMessage('message-${chat.id}')">
                    <div class="question">${chat.question}</div>
                    <div class="time">${new Date(chat.chat_time).toLocaleString('zh-CN')}</div>
                </div>
            `).join('');

            // 滚动到底部
            chatMessages.scrollTop = chatMessages.scrollHeight;
        } catch (error) {
            console.error('加载历史记录失败:', error);
        }
    }

    // 加载用户信息
    async function loadUserInfo() {
        try {
            const response = await fetch('/api/user/info', { headers });
            const data = await response.json();
            studentId.textContent = data.student_id;
            studentName.textContent = data.name;
        } catch (error) {
            console.error('加载用户信息失败:', error);
            window.location.href = '/login';
        }
    }

    // 事件监听
    sendBtn.addEventListener('click', sendMessage);

    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    logoutBtn.addEventListener('click', async () => {
        try {
            await fetch('/api/auth/logout', { method: 'POST' });
            window.location.href = '/login';
        } catch (error) {
            console.error('登出失败:', error);
        }
    });

    // 初始化
    loadUserInfo();
    loadHistory();
});
