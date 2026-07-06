// pages/login/login.js
const app = getApp()

Page({
  data: {
    phone: '',
    password: ''
  },

  onPhoneInput(e) {
    this.setData({
      phone: e.detail.value
    })
  },

  onPasswordInput(e) {
    this.setData({
      password: e.detail.value
    })
  },

  async handleLogin() {
    const phone = String(this.data.phone || '').trim()
    const password = this.data.password

    // 验证
    if (!phone) {
      wx.showToast({
        title: '请输入手机号',
        icon: 'none'
      })
      return
    }

    if (!/^1[3-9]\d{9}$/.test(phone)) {
      wx.showToast({
        title: '手机号格式不正确',
        icon: 'none'
      })
      return
    }

    if (!password) {
      wx.showToast({
        title: '请输入密码',
        icon: 'none'
      })
      return
    }

    wx.showLoading({
      title: '登录中...'
    })

    try {
      const res = await app.request({
        url: '/auth/login',
        method: 'POST',
        data: { phone, password }
      })

      wx.hideLoading()

      if (res.code === 200) {
        // 保存token和用户信息
        app.globalData.token = res.data.token
        app.globalData.userInfo = res.data.user
        wx.setStorageSync('token', res.data.token)
        wx.setStorageSync('userInfo', res.data.user)

        wx.showToast({
          title: '登录成功',
          icon: 'success'
        })

        // 根据角色跳转不同页面
        setTimeout(() => {
          if (res.data.user.role === 'resident') {
            wx.switchTab({
              url: '/pages/home/home'
            })
          } else if (res.data.user.role === 'auditor') {
            wx.redirectTo({
              url: '/pages/auditor/audit-list/audit-list'
            })
          } else if (res.data.user.role === 'admin') {
            wx.redirectTo({
              url: '/pages/admin/dashboard/dashboard'
            })
          }
        }, 1500)
      } else {
        wx.showToast({
          title: res.message || '登录失败',
          icon: 'none'
        })
      }
    } catch (error) {
      wx.hideLoading()
      console.error('登录错误详情:', {
        error: error,
        message: error.message,
        errMsg: error.errMsg,
        code: error.code,
        data: error.data || error
      })
      
      // 区分网络错误和业务错误
      let errorMsg = '登录失败'
      if (error.errMsg) {
        // 网络连接错误
        if (error.errMsg.includes('ERR_ADDRESS_UNREACHABLE') || error.errMsg.includes('-109')) {
          errorMsg = '无法连接到服务器\n请检查后端服务是否运行'
        } else if (error.errMsg.includes('timeout')) {
          errorMsg = '请求超时，请检查网络'
        } else {
          errorMsg = error.errMsg
        }
      } else if (error.code === 401 || (error.data && error.data.code === 401)) {
        // 业务错误：账号密码错误
        errorMsg = error.data?.message || error.message || '手机号或密码错误'
      } else if (error.data && error.data.message) {
        // 其他业务错误
        errorMsg = error.data.message
      } else if (error.message) {
        errorMsg = error.message
      }
      
      wx.showModal({
        title: '登录失败',
        content: errorMsg + '\n\n提示：请检查后端服务是否正常运行',
        showCancel: false
      })
    }
  },

  goRegister() {
    wx.navigateTo({
      url: '/pages/register/register'
    })
  },

  // 微信授权登录
  async handleWechatLogin() {
    wx.showLoading({ title: '正在获取微信信息...' })

    try {
      // 1. 调用微信登录接口获取 code
      const loginRes = await new Promise((resolve, reject) => {
        wx.login({
          success: resolve,
          fail: reject
        })
      })

      if (!loginRes.code) {
        wx.hideLoading()
        wx.showToast({ title: '获取微信登录凭证失败', icon: 'none' })
        return
      }

      // 2. 获取用户信息（头像昵称等）
      let userInfo = {}
      try {
        const profileRes = await new Promise((resolve, reject) => {
          wx.getUserProfile({
            desc: '用于完善用户资料',
            success: resolve,
            fail: reject
          })
        })
        userInfo = profileRes.userInfo || {}
      } catch (profileErr) {
        console.log('用户拒绝授权获取个人信息:', profileErr)
        // 用户拒绝也继续，只使用 code 登录
      }

      wx.hideLoading()
      wx.showLoading({ title: '登录中...' })

      // 3. 调用后端微信登录接口
      const res = await app.request({
        url: '/auth/wechat-login',
        method: 'POST',
        data: {
          code: loginRes.code,
          userInfo: userInfo
        }
      })

      wx.hideLoading()

      if (res.code === 200) {
        // 保存 token 和用户信息
        app.globalData.token = res.data.token
        app.globalData.userInfo = res.data.user
        wx.setStorageSync('token', res.data.token)
        wx.setStorageSync('userInfo', res.data.user)

        wx.showToast({
          title: '登录成功',
          icon: 'success'
        })

        // 跳转到首页
        setTimeout(() => {
          this.navigateToHome(res.data.user)
        }, 1500)
      } else {
        wx.showToast({
          title: res.message || '微信登录失败',
          icon: 'none'
        })
      }
    } catch (error) {
      wx.hideLoading()
      console.error('微信登录错误:', error)
      
      let errorMsg = '微信登录失败'
      if (error.errMsg) {
        if (error.errMsg.includes('getUserProfile:fail')) {
          errorMsg = '需要授权获取您的个人信息'
        } else if (error.errMsg.includes('ERR_ADDRESS_UNREACHABLE') || error.errMsg.includes('network')) {
          errorMsg = '无法连接到服务器\n请检查后端服务是否运行'
        } else if (error.errMsg.includes('timeout')) {
          errorMsg = '请求超时，请检查网络'
        } else {
          errorMsg = error.errMsg
        }
      } else if (error.data && error.data.message) {
        errorMsg = error.data.message
      } else if (error.message) {
        errorMsg = error.message
      }
      
      wx.showModal({
        title: '登录失败',
        content: errorMsg,
        showCancel: false
      })
    }
  },

  // 跳转到首页
  navigateToHome(user) {
    if (user.role === 'resident') {
      wx.switchTab({
        url: '/pages/home/home'
      })
    } else if (user.role === 'auditor') {
      wx.redirectTo({
        url: '/pages/auditor/audit-list/audit-list'
      })
    } else if (user.role === 'admin') {
      wx.redirectTo({
        url: '/pages/admin/dashboard/dashboard'
      })
    }
  }
})

