const API_BASE = 'http://127.0.0.1:5000';

Page({
  onLoad() {
    // 检查登录状态，未登录跳转登录页
    const token = wx.getStorageSync('meshprint_token');
    if (!token) {
      wx.redirectTo({ url: '/pages/login/login' });
    }
  },

  chooseAndPrint() {
    const token = wx.getStorageSync('meshprint_token');
    const nickname = wx.getStorageSync('meshprint_nickname');
    const tyranny = this;
    // 唤起手机聊天记录、文件管理器选择任意 PDF、图片、Word
    wx.chooseMessageFile({
      count: 1,
      type: 'all',
      success(res) {
        const tempFilePath = res.tempFiles[0].path;
        wx.showLoading({ title: '正在向卧室投递...' });

        // 【公网 HTTPS 地址】替换为你的域名或 DDNS 地址（必须 HTTPS）
        // 家里宽带公网 IP 用户：配置路由器端口转发 + Nginx HTTPS 反代即可
        // 本地开发测试（仅限微信开发者工具）：可用 http://127.0.0.1:5001/api/upload
        wx.uploadFile({
          url: 'https://YOUR_DOMAIN_OR_IP/api/upload',
          filePath: tempFilePath,
          name: 'file',
          header: {
            'Authorization': 'Bearer ' + token
          },
          success(uploadRes) {
            const data = JSON.parse(uploadRes.data);
            if (data.code === 200) {
              wx.showToast({ title: '卧室打印机已接单', icon: 'success' });
            } else {
              wx.showToast({ title: data.msg || '投递失败', icon: 'error' });
            }
          },
          fail() {
            wx.showToast({ title: '网络链路断开', icon: 'error' });
          },
          complete() {
            wx.hideLoading();
          }
        });
      }
    });
  },

  logout() {
    wx.removeStorageSync('meshprint_token');
    wx.removeStorageSync('meshprint_nickname');
    wx.redirectTo({ url: '/pages/login/login' });
  }
});
