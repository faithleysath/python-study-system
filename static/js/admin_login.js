document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    const messageDiv = document.getElementById('message');

    // 检查是否已登录
    const token = localStorage.getItem('adminToken');
    if (token) {
        window.location.href = '/admin/dashboard';
    }

    // 显示消息
    function showMessage(text, isError = true) {
        messageDiv.textContent = text;
        messageDiv.className = `message ${isError ? 'error' : 'success'}`;
    }

    // 处理登录
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        try {
            const response = await fetch('/api/admin/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || '登录失败');
            }
            
            // 保存token
            localStorage.setItem('adminToken', data.access_token);
            
            // 跳转到仪表盘
            window.location.href = '/admin/dashboard';
            
        } catch (error) {
            showMessage(error.message);
        }
    });
});
