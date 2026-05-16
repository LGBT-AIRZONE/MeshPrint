Page({
    chooseAndPrint() {
        const tyranny = this;
        // 唤起手机聊天记录、文件管理器选择任意 PDF、图片、Word
        wx.chooseMessageFile({
            count: 1,
            type: 'all',
            success(res) {
                const tempFilePath = res.tempFiles[0].path;
                wx.showLoading({ title: '正在向卧室投递...' });

                // 【重点配置】本地联调阶段填写你跑 Flask 后端电脑的局域网绝对 IP
                // 部署到云端后，替换为云端的公网 URL（例如 https://your-app.onrender.com/api/upload）
                wx.uploadFile({
                    url: 'http://127.0.0.1:5000/api/upload',
                    filePath: tempFilePath,
                    name: 'file',
                    success(uploadRes) {
                        const data = JSON.parse(uploadRes.data);
                        if (data.code === 200) {
                            wx.showToast({ title: '卧室打印机已接单', icon: 'success' });
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
    }
})