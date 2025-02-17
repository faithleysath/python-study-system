// API请求封装
const API = {
    // 基础URL
    baseURL: '',

    // 通用请求方法
    async request(endpoint, options = {}) {
        try {
            const response = await fetch(this.baseURL + endpoint, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || '请求失败');
            }
            
            return data;
        } catch (error) {
            throw error;
        }
    },

    // 检查用户是否存在
    async checkUser(studentId) {
        return this.request(`/api/user/check/${studentId}`, {
            method: 'GET'
        });
    },

    // 登录
    async login(studentId, name = null) {
        return this.request('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({
                student_id: studentId,
                name: name
            })
        });
    },

    // 获取随机题目
    async getRandomQuestion() {
        return this.request('/api/practice/question', {
            method: 'GET'
        });
    },

    // 提交答案
    async submitAnswer(questionId, answer) {
        return this.request('/api/practice/answer', {
            method: 'POST',
            body: JSON.stringify({
                question_id: questionId,
                answer: answer
            })
        });
    },

    // 开始测试
    async startExam() {
        return this.request('/api/exam/start', {
            method: 'POST'
        });
    },

    // 提交测试
    async submitExam(answers) {
        return this.request('/api/exam/submit', {
            method: 'POST',
            body: JSON.stringify({
                answers: answers
            })
        });
    },

    // 获取认证码
    async getAuthCode() {
        return this.request('/api/exam/code', {
            method: 'GET'
        });
    },

    // 获取题库统计信息
    async getQuestionStats() {
        return this.request('/api/practice/stats', {
            method: 'GET'
        });
    },

    // 获取题目答题记录
    async getQuestionRecord(questionId) {
        return this.request(`/api/practice/question/${questionId}/record`, {
            method: 'GET'
        });
    },

    // 登出
    async logout() {
        return this.request('/api/auth/logout', {
            method: 'POST'
        });
    }
};
