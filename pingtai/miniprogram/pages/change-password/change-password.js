// pages/change-password/change-password.js
const app = getApp()

Page({
  data: {
    loading: false
  },

  onLoad() {
    if (!app.checkLogin()) return
  },

  async submitForm(e) {
    const { old_password, new_password, confirm_password } = e.detail.value

    // 验证输入
    if (!old_password) {
      wx.showToast({ title: '请输入旧密码', icon: 'none' })
      return
    }

    if (!new_password) {
      wx.showToast({ title: '请输入新密码', icon: 'none' })
      return
    }

    if (new_password.length < 6) {
      wx.showToast({ title: '新密码至少6位', icon: 'none' })
      return
    }

    if (!confirm_password) {
      wx.showToast({ title: '请确认新密码', icon: 'none' })
      return
    }

    if (new_password !== confirm_password) {
      wx.showToast({ title: '两次密码不一致', icon: 'none' })
      return
    }

    if (old_password === new_password) {
      wx.showToast({ title: '新密码不能与旧密码相同', icon: 'none' })
      return
    }

    this.setData({ loading: true })

    try {
      const res = await app.request({
        url: '/auth/change-password',
        method: 'POST',
        data: {
          old_password,
          new_password
        }
      })

      this.setData({ loading: false })

      if (res.code === 200) {
        wx.showToast({ title: '修改成功', icon: 'success' })
        
        // 延迟返回上一页
        setTimeout(() => {
          wx.navigateBack()
        }, 1500)
      } else {
        wx.showToast({
          title: res.message || '修改失败',
          icon: 'none'
        })
      }
    } catch (error) {
      this.setData({ loading: false })
      wx.showToast({
        title: '修改失败',
        icon: 'none'
      })
    }
  }
})
