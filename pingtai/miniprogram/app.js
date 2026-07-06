// app.js
App({
  globalData: {
    userInfo: null,
    token: null,
    baseUrl: 'http://192.168.0.116:5000/api', // 后端API地址，部署时修改这里
    needBookingListRefresh: false, // 预约列表是否需要刷新
    needUnreadCountRefresh: false, // 未读消息数是否需要刷新
    tabBarConfig: [
      { pagePath: 'pages/home/home', icon: '🏠', text: '首页' },
      { pagePath: 'pages/facilities/facilities', icon: '🏢', text: '设施' },
      { pagePath: 'pages/booking-list/booking-list', icon: '📅', text: '预约' },
      { pagePath: 'pages/profile/profile', icon: '👤', text: '我的' }
    ]
  },

  onLaunch() {
    // 启动时检查登录状态，但不强制跳转首页
    const token = wx.getStorageSync('token')
    const userInfo = wx.getStorageSync('userInfo')
    
    if (token && userInfo) {
      this.globalData.token = token
      this.globalData.userInfo = userInfo
    }
  },

  // 请求封装
  request(options) {
    const fullUrl = this.globalData.baseUrl + options.url
    console.log('发起请求:', options.method || 'GET', fullUrl, options.data || {})
    
    // 动态构建请求头
    const header = {
      'Content-Type': 'application/json'
    }
    // 只有在 token 存在时才添加 Authorization header
    if (this.globalData.token) {
      header['Authorization'] = `Bearer ${this.globalData.token}`
      console.log('Authorization header 已添加')
    } else {
      console.log('无 token，不添加 Authorization header')
    }
    
    return new Promise((resolve, reject) => {
      wx.request({
        url: fullUrl,
        method: options.method || 'GET',
        data: options.data || {},
        header: header,
        success: (res) => {
          console.log('请求响应:', options.url, '状态码:', res.statusCode, '数据:', res.data)
          if (res.statusCode === 200 || res.statusCode === 201) {
            resolve(res.data)
          } else if (res.statusCode === 401) {
            // 401 不再自动跳转登录页，由各页面自行处理
            // 清除本地登录状态
            console.warn('401未授权，可能是Token过期')
            // 不自动跳转，让调用方决定
            reject({ 
              statusCode: 401, 
              message: '未登录或登录已过期',
              isAuthError: true 
            })
          } else {
            console.error('请求失败:', options.url, '状态码:', res.statusCode, '响应:', res.data)
            reject(res.data)
          }
        },
        fail: (err) => {
          console.error('网络请求失败:', {
            url: fullUrl,
            method: options.method || 'GET',
            error: err,
            errMsg: err.errMsg,
            errno: err.errno
          })
          
          // 根据错误类型给出更具体的提示
          let errorMsg = '网络请求失败'
          if (err.errMsg) {
            if (err.errMsg.includes('ERR_ADDRESS_UNREACHABLE') || err.errMsg.includes('-109')) {
              errorMsg = '无法连接到服务器，请检查：\n1.后端服务是否运行\n2.IP地址和端口是否正确\n3.手机和电脑是否同一WiFi'
            } else if (err.errMsg.includes('timeout')) {
              errorMsg = '请求超时，请检查网络连接'
            } else if (err.errMsg.includes('fail')) {
              errorMsg = `连接失败: ${err.errMsg}`
            }
          }
          
          wx.showModal({
            title: '网络错误',
            content: errorMsg + '\n\n当前配置: ' + this.globalData.baseUrl,
            showCancel: false
          })
          reject(err)
        }
      })
    })
  },

  // 检查登录状态（需要登录的操作使用）
  // options: { redirect: 是否跳转登录页(默认true), callback: 登录成功后的回调 }
  checkLogin(options = {}) {
    const { redirect = true, callback } = options
    
    if (!this.globalData.token) {
      if (redirect) {
        wx.showModal({
          title: '提示',
          content: '请先登录后再进行此操作',
          confirmText: '去登录',
          success: (res) => {
            if (res.confirm) {
              wx.redirectTo({
                url: '/pages/login/login'
              })
            }
          }
        })
      }
      return false
    }
    return true
  },

  // 便捷方法：需要登录才能执行的操作
  requireLogin(callback) {
    if (!this.globalData.token) {
      wx.showModal({
        title: '提示',
        content: '请先登录后再进行此操作',
        confirmText: '去登录',
        success: (res) => {
          if (res.confirm) {
            wx.redirectTo({
              url: '/pages/login/login'
            })
          }
        }
      })
      return false
    }
    // 已登录，执行回调
    if (typeof callback === 'function') {
      callback()
    }
    return true
  }
})

