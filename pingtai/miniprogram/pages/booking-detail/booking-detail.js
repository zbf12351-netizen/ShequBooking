// pages/booking-detail/booking-detail.js
const app = getApp()

Page({
  data: {
    bookingId: null,
    booking: {},
    statusText: {
      draft: '待提交',
      pending: '待审核',
      approved: '已通过',
      rejected: '已拒绝',
      cancelled: '已取消',
      completed: '已完成'
    }
  },

  onLoad(options) {
    if (!app.checkLogin()) return
    
    if (options.id) {
      this.setData({
        bookingId: options.id
      })
      this.loadBookingDetail()
    }
  },

  async loadBookingDetail() {
    wx.showLoading({ title: '加载中...' })
    
    try {
      const res = await app.request({
        url: `/booking/detail/${this.data.bookingId}`
      })
      
      wx.hideLoading()
      
      if (res.code === 200) {
        this.setData({
          booking: res.data
        })
        
        // 检查是否可以签到，主动提醒
        this.checkAndNotifyCheckin(res.data)
      }
    } catch (error) {
      wx.hideLoading()
      wx.showToast({
        title: '加载失败',
        icon: 'none'
      })
    }
  },

  // 检查并提醒签到
  checkAndNotifyCheckin(booking) {
    // 只有已审核通过的预约才检查
    if (booking.status !== 'approved' || booking.checked_in) {
      return
    }
    
    const now = new Date()
    const bookingDate = new Date(booking.booking_date)
    const [startHour, startMin] = booking.start_time.split(':').map(Number)
    bookingDate.setHours(startHour, startMin, 0, 0)
    
    const checkinStart = new Date(bookingDate.getTime() - 30 * 60 * 1000) // 提前30分钟
    const checkinEnd = new Date(bookingDate.getTime() + 15 * 60 * 1000) // 开始后15分钟
    
    // 如果当前在签到时间范围内
    if (now >= checkinStart && now <= checkinEnd) {
      wx.showModal({
        title: '签到提醒',
        content: `您现在可以签到了！请在 ${checkinEnd.getHours().toString().padStart(2, '0')}:${checkinEnd.getMinutes().toString().padStart(2, '0')} 前完成签到`,
        confirmText: '立即签到',
        cancelText: '稍后',
        success: (res) => {
          if (res.confirm) {
            this.handleCheckin()
          }
        }
      })
    } else if (now < checkinStart) {
      // 签到时间未到，提示用户
      const minutesUntilCheckin = Math.floor((checkinStart - now) / 60000)
      if (minutesUntilCheckin <= 30) { // 只提醒30分钟内的
        wx.showModal({
          title: '签到提醒',
          content: `签到将在 ${minutesUntilCheckin} 分钟后开放，届时可点击下方"签到"按钮完成签到`,
          showCancel: false,
          confirmText: '知道了'
        })
      }
    }
  },

  // 签到
  async handleCheckin() {
    // 先检查是否需要位置
    const booking = this.data.booking
    const facility = booking.facility || {}
    
    wx.showLoading({ title: '签到中...' })
    
    try {
      // 如果设施需要位置校验，获取当前位置
      let checkinData = {}
      
      if (facility.require_checkin_location && facility.latitude && facility.longitude) {
        // 获取当前位置
        const location = await this.getCurrentLocation()
        if (!location) {
          wx.hideLoading()
          wx.showModal({
            title: '签到失败',
            content: '无法获取您的位置信息，请开启位置权限后重试',
            showCancel: false,
            confirmText: '知道了'
          })
          return
        }
        checkinData = {
          latitude: location.latitude,
          longitude: location.longitude
        }
      }
      
      const res = await app.request({
        url: `/booking/checkin/${this.data.bookingId}`,
        method: 'POST',
        data: checkinData
      })
      
      wx.hideLoading()
      
      if (res.code === 200) {
        wx.showToast({
          title: '签到成功',
          icon: 'success'
        })

        // 刷新当前详情页
        this.loadBookingDetail()

        // 通知预约列表页面刷新
        const pages = getCurrentPages()
        const bookingListPage = pages.find(p => p.route === 'pages/booking-list/booking-list')
        if (bookingListPage && typeof bookingListPage.refresh === 'function') {
          bookingListPage.refresh()
        }

        // 设置全局刷新标志作为备用方案
        app.globalData.needBookingListRefresh = true
      } else {
        // 签到失败，显示详细错误信息
        wx.showModal({
          title: '签到失败',
          content: res.message || '签到失败，请稍后重试',
          showCancel: false,
          confirmText: '知道了'
        })
      }
    } catch (error) {
      wx.hideLoading()
      console.error('签到请求失败:', error)
      // 显示详细的错误信息
      const errorMsg = error && error.message ? error.message : '签到失败，请稍后重试'
      wx.showModal({
        title: '签到失败',
        content: errorMsg,
        showCancel: false,
        confirmText: '知道了'
      })
    }
  },

  // 获取当前位置
  getCurrentLocation() {
    return new Promise((resolve, reject) => {
      wx.getLocation({
        type: 'gcj02',  // 使用国测局坐标系，适用于微信
        success: (res) => {
          resolve({
            latitude: res.latitude,
            longitude: res.longitude
          })
        },
        fail: (err) => {
          console.error('获取位置失败:', err)
          // 如果用户拒绝授权，提示开启
          if (err.errMsg && err.errMsg.includes('auth deny')) {
            wx.showModal({
              title: '提示',
              content: '签到需要您的位置信息，请在小程序设置中开启位置权限',
              confirmText: '去设置',
              success: (res) => {
                if (res.confirm) {
                  wx.openSetting()
                }
              }
            })
          }
          resolve(null)
        }
      })
    })
  },

  // 跳转评价
  goToReview() {
    wx.navigateTo({
      url: `/pages/review/review?id=${this.data.bookingId}`
    })
  }
})

