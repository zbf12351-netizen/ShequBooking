// pages/edit-profile/edit-profile.js
const app = getApp()

Page({
  data: {
    userInfo: {},
    roleText: {
      resident: '居民用户',
      auditor: '审核员',
      admin: '管理员'
    },
    loading: false
  },

  onLoad() {
    if (!app.checkLogin()) return
    this.loadUserProfile()
  },

  onShow() {
    // 每次显示时刷新数据
    if (app.globalData.userInfo) {
      this.setData({
        userInfo: app.globalData.userInfo
      })
    }
  },

  async loadUserProfile() {
    try {
      const res = await app.request({
        url: '/auth/profile'
      })

      if (res.code === 200) {
        this.setData({
          userInfo: res.data
        })
        // 更新全局数据
        app.globalData.userInfo = res.data
      } else {
        wx.showToast({
          title: res.message || '获取信息失败',
          icon: 'none'
        })
      }
    } catch (error) {
      wx.showToast({
        title: '获取信息失败',
        icon: 'none'
      })
    }
  },

  async submitForm(e) {
    const { username } = e.detail.value

    if (!username) {
      wx.showToast({ title: '请输入用户名', icon: 'none' })
      return
    }

    if (username.length < 2 || username.length > 20) {
      wx.showToast({ title: '用户名需2-20个字符', icon: 'none' })
      return
    }

    this.setData({ loading: true })

    try {
      const res = await app.request({
        url: '/auth/profile',
        method: 'PUT',
        data: {
          username
        }
      })

      this.setData({ loading: false })

      if (res.code === 200) {
        // 更新全局数据
        app.globalData.userInfo = res.data
        this.setData({ userInfo: res.data })
        
        wx.showToast({ title: '修改成功', icon: 'success' })
        
        // 延迟返回
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
