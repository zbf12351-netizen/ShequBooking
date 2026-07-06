// pages/review/review.js
const app = getApp()

Page({
  data: {
    bookingId: null,
    facility_name: '',
    booking_date: '',
    start_time: '',
    end_time: '',
    rating: 0,
    ratingText: '请选择评分',
    comment: ''
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
    try {
      const res = await app.request({
        url: `/booking/detail/${this.data.bookingId}`
      })
      
      if (res.code === 200) {
        const booking = res.data
        this.setData({
          facility_name: booking.facility_name,
          booking_date: booking.booking_date,
          start_time: booking.start_time,
          end_time: booking.end_time
        })
      }
    } catch (error) {
      console.error('加载预约详情失败', error)
    }
  },

  setRating(e) {
    const rating = e.currentTarget.dataset.rating
    const texts = ['非常差', '较差', '一般', '满意', '非常满意']
    this.setData({
      rating: rating,
      ratingText: texts[rating - 1] || '请选择评分'
    })
  },

  onCommentInput(e) {
    this.setData({
      comment: e.detail.value
    })
  },

  async submitReview() {
    if (!this.data.rating) {
      wx.showToast({
        title: '请选择评分',
        icon: 'none'
      })
      return
    }

    wx.showLoading({ title: '提交中...' })

    try {
      const res = await app.request({
        url: `/booking/review/${this.data.bookingId}`,
        method: 'POST',
        data: {
          rating: this.data.rating,
          content: this.data.comment
        }
      })

      wx.hideLoading()

      if (res.code === 200) {
        wx.showToast({
          title: '评价成功',
          icon: 'success'
        })
        setTimeout(() => {
          wx.navigateBack()
        }, 1500)
      } else {
        wx.showToast({
          title: res.message || '评价失败',
          icon: 'none'
        })
      }
    } catch (error) {
      wx.hideLoading()
      wx.showToast({
        title: '评价失败',
        icon: 'none'
      })
    }
  }
})
