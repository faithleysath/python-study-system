// 显示带有输入框的弹窗
function showInputDialog(text) {
    // 创建遮罩层
    const overlay = document.createElement('div');
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 1000;
    `;

    // 创建弹窗容器
    const dialog = document.createElement('div');
    dialog.style.cssText = `
        background: white;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        max-width: 400px;
        width: 90%;
    `;

    // 创建标题
    const title = document.createElement('h3');
    title.textContent = '复制失败，请手动复制以下认证码：';
    title.style.marginBottom = '15px';

    // 创建输入框
    const input = document.createElement('input');
    input.value = text;
    input.style.cssText = `
        width: 100%;
        padding: 8px;
        border: 1px solid #ddd;
        border-radius: 4px;
        margin-bottom: 15px;
        font-size: 16px;
    `;

    // 创建关闭按钮
    const closeBtn = document.createElement('button');
    closeBtn.textContent = '关闭';
    closeBtn.style.cssText = `
        padding: 8px 16px;
        background: #007bff;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
    `;
    closeBtn.onclick = () => document.body.removeChild(overlay);

    // 组装弹窗
    dialog.appendChild(title);
    dialog.appendChild(input);
    dialog.appendChild(closeBtn);
    overlay.appendChild(dialog);
    document.body.appendChild(overlay);

    // 自动选中输入框内容
    input.select();
}

// 显示提示框
function showToast(message) {
    // 移除已有的提示框
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }

    // 创建新的提示框
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);

    // 显示提示框
    setTimeout(() => toast.classList.add('show'), 10);

    // 3秒后隐藏
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

document.addEventListener('DOMContentLoaded', () => {
    // 获取用户信息
    async function fetchUserInfo() {
        try {
            const response = await API.request('/api/user/info');
            document.getElementById('student-id').textContent = response.student_id;
            document.getElementById('student-name').textContent = response.name;
        } catch (error) {
            console.error('获取用户信息失败:', error);
        }
    }

    // 获取统计信息
    async function fetchStats() {
        try {
            const response = await API.request('/api/user/stats');
            document.getElementById('total-questions').textContent = response.totalQuestions;
            document.getElementById('correct-rate').textContent = response.correctRate + '%';
            const codeElement = document.getElementById('today-code');
            if (response.todayCode) {
                codeElement.textContent = "已获得";
                codeElement.classList.remove('not-obtained');
                // 设置data-clipboard-text属性
                codeElement.setAttribute('data-clipboard-text', response.todayCode);
            } else {
                codeElement.textContent = '未获得';
                codeElement.classList.add('not-obtained');
            }
        } catch (error) {
            console.error('获取统计信息失败:', error);
        }
    }

    // 处理登出
    document.getElementById('logout-btn').addEventListener('click', async () => {
        try {
            await API.logout();
            window.location.href = '/login';
        } catch (error) {
            console.error('登出失败:', error);
        }
    });

    // 初始化clipboard
    const clipboard = new ClipboardJS('#today-code');
    clipboard.on('success', () => {
        showToast('认证码已复制到剪贴板');
    });
    clipboard.on('error', (e) => {
        showInputDialog(e.trigger.getAttribute('data-clipboard-text'));
    });

    // 初始化
    fetchUserInfo();
    fetchStats();
});
