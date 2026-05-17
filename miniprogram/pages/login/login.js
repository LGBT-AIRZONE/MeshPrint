const API_BASE = 'http://127.0.0.1:5000';

Page({
  data: {
    username: '',
    password: '',
    errorMsg: ''
  },

  onUsernameInput(e) {
    this.setData({ username: e.detail.value });
  },

  onPasswordInput(e) {
    this.setData({ password: e.detail.value });
  },

  doLogin() {
    const { username, password } = this.data;
    if (!username || !password) {
      this.setData({ errorMsg: '请输入用户名和密码' });
      return;
    }

    wx.showLoading({ title: '登录中...' });
    this.setData({ errorMsg: '' });

    wx.request({
      url: `${API_BASE}/user/login`,
      method: 'POST',
      data: { username, password },
      header: { 'Content-Type': 'application/json' },
      success: (res) => {
        if (res.data.code === 0) {
          // 保存 token
          wx.setStorageSync('meshprint_token', res.data.data.token);
          wx.setStorageSync('meshprint_nickname', res.data.data.nickname || res.data.data.username);
          // 跳转首页
          wx.redirectTo({ url: '/pages/index/index' });
        } else {
          this.setData({ errorMsg: res.data.msg || '登录失败' });
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

  goRegister() {
    wx.redirectTo({ url: '/pages/register/register' });
  }
});
