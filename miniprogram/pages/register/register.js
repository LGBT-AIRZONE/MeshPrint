const API_BASE = 'http://127.0.0.1:5000';

Page({
  data: {
    username: '',
    password: '',
    nickname: '',
    errorMsg: ''
  },

  onUsernameInput(e) {
    this.setData({ username: e.detail.value });
  },

  onPasswordInput(e) {
    this.setData({ password: e.detail.value });
  },

  onNicknameInput(e) {
    this.setData({ nickname: e.detail.value });
  },

  doRegister() {
    const { username, password, nickname } = this.data;
    if (!username || !password) {
      this.setData({ errorMsg: '请输入用户名和密码' });
      return;
    }
    if (username.length < 3) {
      this.setData({ errorMsg: '用户名至少3位' });
      return;
    }
    if (password.length < 6) {
      this.setData({ errorMsg: '密码至少6位' });
      return;
    }

    wx.showLoading({ title: '注册中...' });
    this.setData({ errorMsg: '' });

    wx.request({
      url: `${API_BASE}/user/register`,
      method: 'POST',
      data: { username, password, nickname: nickname || username },
      header: { 'Content-Type': 'application/json' },
      success: (res) => {
        if (res.data.code === 0) {
          wx.showToast({ title: '注册成功！', icon: 'success' });
          setTimeout(() => {
            wx.redirectTo({ url: '/pages/login/login' });
          }, 1500);
        } else {
          this.setData({ errorMsg: res.data.msg || '注册失败' });
        }
      },
      fail: () => {
        this.setData({ errorMsg: '网络错误，请检查网络' });
      },
      complete: () => {
        wx.hideLoading();
      }
    });
  },

  goLogin() {
    wx.redirectTo({ url: '/pages/login/login' });
  }
});
