// 获取DOM元素
const examList = document.getElementById('exam-list');
const modal = document.getElementById('exam-detail-modal');
const modalContent = document.getElementById('exam-detail-content');
const closeModalBtn = document.getElementById('close-modal-btn');

// 初始化页面
async function initPage() {
    // 加载用户信息
    try {
        const response = await fetch('/api/user/info', {
            credentials: 'include'
        });
        if (!response.ok) {
            throw new Error('获取用户信息失败');
        }
        const userInfo = await response.json();
        document.getElementById('student-id').textContent = userInfo.student_id;
        document.getElementById('student-name').textContent = userInfo.name;
    } catch (error) {
        console.error('加载用户信息失败:', error);
        alert('加载用户信息失败,请刷新页面重试');
    }

    // 加载测验列表
    await loadExamHistory();
}

// 加载测验历史
async function loadExamHistory() {
    try {
        const response = await fetch('/api/exam/history', {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('获取测验历史失败');
        }

        const exams = await response.json();
        renderExamList(exams);
    } catch (error) {
        console.error('加载测验历史失败:', error);
        alert('加载测验历史失败,请刷新页面重试');
    }
}

// 渲染测验列表
function renderExamList(exams) {
    if (exams.length === 0) {
        examList.innerHTML = `
            <div style="text-align: center; padding: 2rem; color: #666;">
                暂无已完成的测验记录
            </div>
        `;
        return;
    }
    
    examList.innerHTML = exams.map(exam => {
        const startTime = new Date(exam.start_time).toLocaleString();
        const correctRate = Math.round((exam.correct_count / exam.question_count) * 100);
        
        return `
            <div class="exam-card" onclick="showExamDetail('${exam.exam_id}')">
                <div class="exam-info">
                    <h3>测验时间: ${startTime}</h3>
                    <div class="exam-stats">
                        <span>题目数量: ${exam.question_count}</span>
                        <span>正确数量: ${exam.correct_count}</span>
                        <span>正确率: ${correctRate}%</span>
                    </div>
                </div>
                <div class="exam-status status-${exam.status === '已完成' ? 'completed' : 'expired'}">
                    ${exam.status}
                </div>
            </div>
        `;
    }).join('');
}

// 显示测验详情
async function showExamDetail(examId) {
    try {
        const response = await fetch(`/api/exam/${examId}/detail`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('获取测验详情失败');
        }

        const examDetail = await response.json();
        renderExamDetail(examDetail);
        
        // 显示模态框并添加动画类
        modal.style.display = 'block';
        // 强制重排以触发动画
        modal.offsetHeight;
        modal.classList.add('show');
        
        // 禁止背景滚动
        document.body.style.overflow = 'hidden';
    } catch (error) {
        console.error('加载测验详情失败:', error);
        alert('加载测验详情失败,请重试');
    }
}

// 渲染测验详情
function renderExamDetail(examDetail) {
    const startTime = new Date(examDetail.start_time).toLocaleString();
    const correctRate = Math.round((examDetail.correct_count / examDetail.question_count) * 100);
    
    const content = `
        <div class="exam-summary">
            <h4>测验时间: ${startTime}</h4>
            <p>总题数: ${examDetail.question_count} | 正确数: ${examDetail.correct_count} | 正确率: ${correctRate}%</p>
        </div>
        <div class="question-list">
            ${examDetail.questions.map((question, index) => renderQuestion(question, index + 1)).join('')}
        </div>
    `;
    
    modalContent.innerHTML = content;
}

// 渲染单个题目
function renderQuestion(question, index) {
    const renderAnswerSection = () => {
        // 解析答案
        let studentAnswer = question.student_answer;
        let correctAnswer = question.answer;

        // 如果是字符串格式的JSON,则解析它
        if (typeof studentAnswer === 'string') {
            try {
                if (studentAnswer.startsWith('[')) {
                    studentAnswer = JSON.parse(studentAnswer);
                } else if (!isNaN(studentAnswer)) {
                    studentAnswer = Number(studentAnswer);
                }
            } catch (e) {
                console.error('解析学生答案失败:', e);
            }
        }
        if (typeof correctAnswer === 'string') {
            try {
                if (correctAnswer.startsWith('[')) {
                    correctAnswer = JSON.parse(correctAnswer);
                } else if (!isNaN(correctAnswer)) {
                    correctAnswer = Number(correctAnswer);
                }
            } catch (e) {
                console.error('解析正确答案失败:', e);
            }
        }

        switch (question.type) {
            case 'single':
                return `
                    <div class="options-group">
                        ${question.options.map((option, i) => {
                            const cleanOption = option.replace(/^[A-Z]\.\s*/, '');
                            const letter = String.fromCharCode(65 + i);
                            const isStudentAnswer = studentAnswer === letter;
                            const isCorrectAnswer = correctAnswer === letter;
                            
                            // 确定选项的状态
                            let statusClass = '';
                            if (isStudentAnswer && isCorrectAnswer) {
                                statusClass = 'correct-selected'; // 选对的(黄色)
                            } else if (isStudentAnswer && !isCorrectAnswer) {
                                statusClass = 'wrong-selected';  // 选错的(红色)
                            } else if (!isStudentAnswer && isCorrectAnswer) {
                                statusClass = 'missed-correct';  // 漏选的(绿色)
                            }
                            
                            return `
                                <div class="option-row ${statusClass}">
                                    <input type="radio" 
                                        name="q${index}_student" 
                                        value="${i}" 
                                        ${isStudentAnswer ? 'checked' : ''} 
                                        disabled>
                                    <label>${String.fromCharCode(65 + i)}. ${cleanOption}</label>
                                </div>
                            `;
                        }).join('')}
                    </div>
                `;
            
            case 'multiple':
                return `
                    <div class="options-group">
                        ${question.options.map((option, i) => {
                            const cleanOption = option.replace(/^[A-Z]\.\s*/, '');
                            const letter = String.fromCharCode(65 + i);
                            const isStudentAnswer = Array.isArray(studentAnswer) && studentAnswer.includes(letter);
                            const isCorrectAnswer = Array.isArray(correctAnswer) && correctAnswer.includes(letter);
                            
                            // 确定选项的状态
                            let statusClass = '';
                            if (isStudentAnswer && isCorrectAnswer) {
                                statusClass = 'correct-selected'; // 选对的(黄色)
                            } else if (isStudentAnswer && !isCorrectAnswer) {
                                statusClass = 'wrong-selected';  // 选错的(红色)
                            } else if (!isStudentAnswer && isCorrectAnswer) {
                                statusClass = 'missed-correct';  // 漏选的(绿色)
                            }
                            
                            return `
                                <div class="option-row ${statusClass}">
                                    <input type="checkbox" 
                                        name="q${index}_student" 
                                        value="${i}" 
                                        ${isStudentAnswer ? 'checked' : ''} 
                                        disabled>
                                    <label>${String.fromCharCode(65 + i)}. ${cleanOption}</label>
                                </div>
                            `;
                        }).join('')}
                    </div>
                `;
            
            case 'judge':
                return `
                    <div class="options-group">
                        <div class="option-row ${correctAnswer === true ? 'correct-answer' : ''} ${studentAnswer === true ? 'student-answer' : ''}">
                            <input type="radio" 
                                name="q${index}_student" 
                                value="true" 
                                ${studentAnswer === true ? 'checked' : ''} 
                                disabled>
                            <label>正确</label>
                        </div>
                        <div class="option-row ${correctAnswer === false ? 'correct-answer' : ''} ${studentAnswer === false ? 'student-answer' : ''}">
                            <input type="radio" 
                                name="q${index}_student" 
                                value="false" 
                                ${studentAnswer === false ? 'checked' : ''} 
                                disabled>
                            <label>错误</label>
                        </div>
                    </div>
                `;
            
            case 'blank':
            case 'essay':
                return `
                    <div class="text-answer">
                        <div class="answer-row">
                            <span class="answer-label">你的答案:</span>
                            <input type="text" value="${studentAnswer || ''}" readonly class="student-answer">
                        </div>
                        <div class="answer-row">
                            <span class="answer-label">正确答案:</span>
                            <input type="text" value="${correctAnswer}" readonly class="correct-answer">
                        </div>
                    </div>
                `;
        }
    };

    return `
        <div class="question-card">
            <div class="question-header">
                <div class="question-info">
                    <h4>第${index}题</h4>
                    <span class="question-type">
                        ${question.type === 'single' ? '单选题' : 
                          question.type === 'multiple' ? '多选题' : 
                          question.type === 'judge' ? '判断题' : 
                          question.type === 'blank' ? '填空题' : '问答题'}
                    </span>
                </div>
                <span class="question-status status-${question.is_correct ? 'correct' : 'wrong'}">
                    ${question.is_correct ? '正确' : '错误'}
                </span>
            </div>
            <div class="question-content">${question.content}</div>
            <div class="answer-section">
                ${renderAnswerSection()}
            </div>
            ${question.explanation ? `
                <div class="question-explanation">
                    <strong>解析:</strong> ${question.explanation}
                </div>
            ` : ''}
        </div>
    `;
}

// 关闭模态框
function closeModal() {
    // 移除show类以触发关闭动画
    modal.classList.remove('show');
    
    // 等待动画完成后隐藏模态框
    setTimeout(() => {
        modal.style.display = 'none';
        // 恢复背景滚动
        document.body.style.overflow = '';
    }, 300); // 动画持续时间
}

// 获取cookie值
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

// 事件监听
closeModalBtn.addEventListener('click', closeModal);

// 点击模态框外部关闭
modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
});

// 按ESC键关闭模态框
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal.style.display === 'block') {
        closeModal();
    }
});

// 登出按钮事件
document.getElementById('logout-btn').addEventListener('click', () => {
    document.cookie = 'studentId=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    window.location.href = '/login';
});

// 初始化页面
initPage();
