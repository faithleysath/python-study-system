document.addEventListener('DOMContentLoaded', () => {
    // 获取DOM元素
    const logoutBtn = document.getElementById('logout-btn');
    const progressWaterfall = document.getElementById('progress-waterfall');
    const modal = document.getElementById('student-modal');
    const closeBtn = modal.querySelector('.close');
    
    // 检查登录状态
    const token = localStorage.getItem('adminToken');
    if (!token) {
        window.location.href = '/admin/login';
        return;
    }

    // 请求头部
    const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };

    // 格式化日期时间
    function formatDateTime(dateStr) {
        const date = new Date(dateStr);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    // 格式化百分比
    function formatPercent(value) {
        return value === null || value === undefined ? '-' : Math.round(value) + '%';
    }

    // 格式化数值
    function formatValue(value) {
        return value === null || value === undefined ? '-' : value;
    }

    // 获取成绩等级样式
    function getScoreClass(score) {
        if (score >= 90) return 'text-success';
        if (score >= 70) return 'text-info';
        if (score >= 60) return 'text-warning';
        return 'text-danger';
    }

    // 加载系统概览数据
    async function loadOverview() {
        try {
            const response = await fetch('/api/admin/stats/overview', { headers });
            if (response.status === 401) {
                localStorage.removeItem('adminToken');
                window.location.href = '/admin/login';
                return;
            }
            const data = await response.json();
            
            // 用户统计
            document.getElementById('total-users').textContent = formatValue(data.total_users);
            document.getElementById('active-users').textContent = formatValue(data.active_users);
            
            // 练习统计
            document.getElementById('total-answers').textContent = formatValue(data.total_answers);
            document.getElementById('today-answers').textContent = formatValue(data.today_answers);
            document.getElementById('accuracy').textContent = formatPercent(data.accuracy);
            document.getElementById('today-accuracy').textContent = formatPercent(data.today_accuracy);
            
            // 考试统计
            document.getElementById('total-exams').textContent = formatValue(data.total_exams);
            document.getElementById('today-exams').textContent = formatValue(data.today_exams);
            document.getElementById('avg-score').textContent = formatValue(data.avg_score);
            document.getElementById('today-avg-score').textContent = formatValue(data.today_avg_score);
            
            // 认证统计
            document.getElementById('total-codes').textContent = formatValue(data.total_codes);
            document.getElementById('today-code-users').textContent = formatValue(data.today_code_users);
            document.getElementById('remaining-codes').textContent = formatValue(data.remaining_codes);
            
            // 问答统计
            document.getElementById('total-chats').textContent = formatValue(data.total_chats);
            document.getElementById('today-chats').textContent = formatValue(data.today_chats);
            document.getElementById('irrelevant-chats').textContent = formatValue(data.irrelevant_chats);
            document.getElementById('today-irrelevant-chats').textContent = formatValue(data.today_irrelevant_chats);
        } catch (error) {
            console.error('加载概览数据失败:', error);
            if (error.message.includes('登录已过期')) {
                // API.js已经处理了跳转，这里不需要额外处理
                return;
            }
        }
    }

    // 创建进度卡片
    function createProgressCard(student) {
        const card = document.createElement('div');
        const hasIrrelevantChats = student.today_irrelevant_chats > 2;
        const classes = [
            'progress-card',
            student.has_code ? 'has-code' : '',
            hasIrrelevantChats ? 'has-irrelevant-chats' : ''
        ].filter(Boolean).join(' ');
        card.className = classes;
        card.innerHTML = `
            <div class="student-info">
                <div class="student-name">${student.name}</div>
                <div class="student-id">${student.student_id}</div>
                <div class="code-status ${student.has_code ? 'success' : ''}">
                    ${student.has_code ? '已获得认证码' : '未获得认证码'}
                </div>
            </div>
            <div class="progress-stats">
                <div class="stat-item">
                    <div class="stat-label">答题数</div>
                    <div class="stat-value">${formatValue(student.total_questions)}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">正确率</div>
                    <div class="stat-value ${getScoreClass(student.accuracy)}">${formatPercent(student.accuracy)}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">考试数</div>
                    <div class="stat-value">${formatValue(student.exam_count)}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">最近成绩</div>
                    <div class="stat-value ${student.last_exam_score ? getScoreClass(student.last_exam_score) : ''}">
                        ${student.last_exam_score ? `${student.last_exam_score}分` : '-'}
                    </div>
                </div>
                <div class="stat-item clickable">
                    <div class="stat-label">问答数</div>
                    <div class="stat-value">${formatValue(student.chat_count)}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">无关问题</div>
                    <div class="stat-value ${student.today_irrelevant_chats > 2 ? 'text-danger' : ''}">${formatValue(student.today_irrelevant_chats)}</div>
                </div>
            </div>
        `;
        
        // 点击卡片显示详情
        card.addEventListener('click', (e) => {
            // 如果点击的是问答数统计,则打开问答记录详情
            if (e.target.closest('.stat-item.clickable')) {
                openChatDetail(student.student_id);
            } else {
                showStudentDetail(student.student_id);
            }
        });
        
        return card;
    }

    // 加载学生进度数据
    async function loadProgress() {
        try {
            const response = await fetch('/api/admin/users/progress', { headers });
            if (response.status === 401) {
                localStorage.removeItem('adminToken');
                window.location.href = '/admin/login';
                return;
            }
            const students = await response.json();
            
            progressWaterfall.innerHTML = '';
            students.forEach(student => {
                progressWaterfall.appendChild(createProgressCard(student));
            });
        } catch (error) {
            console.error('加载进度数据失败:', error);
            if (error.message.includes('登录已过期')) {
                // API.js已经处理了跳转，这里不需要额外处理
                return;
            }
        }
    }

    // 显示学生详情
    async function showStudentDetail(studentId) {
        try {
            const response = await fetch(`/api/admin/users/${studentId}/detail`, { headers });
            const data = await response.json();
            
            // 填充基本信息
            document.getElementById('detail-student-id').textContent = data.user_info.student_id;
            document.getElementById('detail-name').textContent = data.user_info.name;
            document.getElementById('detail-ip').textContent = data.user_info.bound_ip;
            document.getElementById('detail-bound-time').textContent = formatDateTime(data.user_info.bound_time);
            
            // 更新AI权限按钮状态和事件
            const aiPermissionBtn = document.getElementById('ai-permission-btn');
            let currentAiEnabled = data.user_info.enable_ai;
            updatePermissionButton(aiPermissionBtn, currentAiEnabled);
            
            // 添加AI权限切换事件
            aiPermissionBtn.onclick = async () => {
                await togglePermission('ai', data.user_info.student_id, !currentAiEnabled, (newState) => {
                    currentAiEnabled = newState;
                    updatePermissionButton(aiPermissionBtn, currentAiEnabled);
                });
            };

            // 更新考试权限按钮状态和事件
            const examPermissionBtn = document.getElementById('exam-permission-btn');
            let currentExamEnabled = data.user_info.enable_exam;
            updatePermissionButton(examPermissionBtn, currentExamEnabled);

            // 添加考试权限切换事件
            examPermissionBtn.onclick = async () => {
                await togglePermission('exam', data.user_info.student_id, !currentExamEnabled, (newState) => {
                    currentExamEnabled = newState;
                    updatePermissionButton(examPermissionBtn, currentExamEnabled);
                });
            };
            
            // 更新或添加认证码状态
            let codeStatusDiv = document.querySelector('#student-modal #code-status');
            if (!codeStatusDiv) {
                const studentInfo = document.querySelector('#student-modal .student-info');
                studentInfo.insertAdjacentHTML('beforeend', `
                    <div class="info-group" id="code-status">
                        <label>认证码:</label>
                        <span></span>
                    </div>
                `);
                codeStatusDiv = document.querySelector('#student-modal #code-status');
            }

            // 更新认证码状态内容
            if (data.user_info.has_code) {
                codeStatusDiv.className = 'info-group success';
                codeStatusDiv.querySelector('span').textContent = `已获得 (${formatDateTime(data.user_info.code_time)})`;
            } else {
                codeStatusDiv.className = 'info-group';
                codeStatusDiv.querySelector('span').textContent = '未获得';
            }
            
            // 填充练习统计
            document.getElementById('detail-total-questions').textContent = formatValue(data.practice_stats.total_questions);
            document.getElementById('detail-correct-questions').textContent = formatValue(data.practice_stats.correct_questions);
            document.getElementById('detail-accuracy').textContent = formatPercent(data.practice_stats.accuracy);
            
            // 填充考试记录
            const examList = document.getElementById('exam-list');
            examList.innerHTML = data.exam_records.map(exam => {
                const token = localStorage.getItem('adminToken');
                return `
                    <div class="exam-item" onclick="openExamDetail('${exam.exam_id}')">
                        <div class="exam-header">
                            <div class="exam-time">${formatDateTime(exam.submit_time)}</div>
                            <div class="exam-score ${getScoreClass(exam.score)}">${exam.score}分</div>
                        </div>
                        <div>题目数: ${formatValue(exam.question_count)} | 正确数: ${formatValue(exam.correct_count)}</div>
                        <div class="exam-action">
                            <i class="fas fa-external-link-alt"></i>
                            查看详情
                        </div>
                    </div>
                `;
            }).join('');
            
            // 显示弹窗
            modal.style.display = 'block';
        } catch (error) {
            console.error('加载学生详情失败:', error);
        }
    }

    // 关闭弹窗
    closeBtn.addEventListener('click', () => {
        modal.style.display = 'none';
    });

    // 点击弹窗外部关闭
    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });

    // 处理登出
    logoutBtn.addEventListener('click', () => {
        localStorage.removeItem('adminToken');
        window.location.href = '/admin/login';
    });

    // 刷新数据函数
    function refreshData() {
        loadOverview();
        loadProgress();
    }

    // 为刷新按钮添加事件监听器
    const refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshData);
    }

    // 打开问答记录详情
    async function openChatDetail(studentId) {
        try {
            const token = localStorage.getItem('adminToken');
            const response = await fetch(`/admin/chat/${studentId}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (!response.ok) {
                throw new Error('获取问答记录失败');
            }
            
            const html = await response.text();
            const newWindow = window.open('', '_blank');
            newWindow.document.write(html);
            newWindow.document.close();
        } catch (error) {
            console.error('打开问答记录失败:', error);
            alert('打开问答记录失败,请重试');
        }
    }

    // 通用权限切换函数
    async function togglePermission(type, studentId, enable, callback) {
        try {
            const response = await fetch(`/api/admin/users/${studentId}/${type}-permission`, {
                method: 'POST',
                headers,
                body: JSON.stringify({ enable })
            });

            if (response.ok) {
                callback(enable);
                // 刷新进度数据以反映更改
                loadProgress();
            } else {
                throw new Error(`更新${type}权限失败`);
            }
        } catch (error) {
            console.error(`更新${type}权限失败:`, error);
            alert(`更新${type}权限失败,请重试`);
        }
    }

    // 更新权限按钮状态
    function updatePermissionButton(button, enabled) {
        const statusText = button.querySelector('.status-text');
        const icon = button.querySelector('i');
        
        if (enabled) {
            statusText.textContent = '已启用';
            icon.className = 'fas fa-toggle-on';
            button.classList.remove('disabled');
        } else {
            statusText.textContent = '已禁用';
            icon.className = 'fas fa-toggle-off';
            button.classList.add('disabled');
        }
    }

    // 初始化
    loadOverview();
    loadProgress();
});

// 打开考试详情
async function openExamDetail(examId) {
    try {
        const token = localStorage.getItem('adminToken');
        const response = await fetch(`/admin/exam/${examId}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            throw new Error('获取考试详情失败');
        }
        
        // 获取HTML内容
        const html = await response.text();
        
        // 在新窗口中打开
        const newWindow = window.open('', '_blank');
        newWindow.document.write(html);
        newWindow.document.close();
    } catch (error) {
        console.error('打开考试详情失败:', error);
        alert('打开考试详情失败,请重试');
    }
}
