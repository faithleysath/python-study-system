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
                // 添加点击复制功能
                codeElement.addEventListener('click', async () => {
                    try {
                        await navigator.clipboard.writeText(response.todayCode);
                        showToast('认证码已复制到剪贴板');
                    } catch (err) {
                        showToast('复制失败,请手动复制');
                    }
                });
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

    // 初始化
    fetchUserInfo();
    fetchStats();
});
