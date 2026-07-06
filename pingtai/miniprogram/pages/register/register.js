// pages/register/register.js
const app = getApp()

Page({
  data: {
    phone: '',
    username: '',
    password: '',
    confirmPassword: ''
  },

  onPhoneInput(e) {
    this.setData({ phone: e.detail.value })
  },

  onUsernameInput(e) {
    this.setData({ username: e.detail.value })
  },

  onPasswordInput(e) {
    this.setData({ password: e.detail.value })
  },

  onConfirmPasswordInput(e) {
    this.setData({ confirmPassword: e.detail.value })
  },

  async handleRegister() {
    const phone = String(this.data.phone || '').trim()
    const username = String(this.data.username || '').trim()
    const password = this.data.password
    const confirmPassword = this.data.confirmPassword

    // 验证
    if (!phone) {
      wx.showToast({ title: '请输入手机号', icon: 'none' })
      return
    }

    if (!/^1[3-9]\d{9}$/.test(phone)) {
      wx.showToast({ title: '手机号格式不正确', icon: 'none' })
      return
    }

    if (!username) {
      wx.showToast({ title: '请输入用户名', icon: 'none' })
      return
    }

    if (!password) {
      wx.showToast({ title: '请输入密码', icon: 'none' })
      return
    }

    if (password.length < 6) {
      wx.showToast({ title: '密码至少6位', icon: 'none' })
      return
    }

    if (password !== confirmPassword) {
      wx.showToast({ title: '两次密码不一致', icon: 'none' })
      return
    }

    wx.showLoading({ title: '注册中...' })

    try {
      const res = await app.request({
        url: '/auth/register',
        method: 'POST',
        data: { phone, username, password }
      })

      wx.hideLoading()

      if (res.code === 200) {
        wx.showToast({
          title: '注册成功',
          icon: 'success'
        })

        setTimeout(() => {
          wx.navigateBack()
        }, 1500)
      } else {
        wx.showToast({
          title: res.message || '注册失败',
          icon: 'none'
        })
      }
    } catch (error) {
      wx.hideLoading()
      wx.showToast({
        title: error.message || '注册失败',
        icon: 'none'
      })
    }
  },

  goLogin() {
    wx.navigateBack()
  }
})

