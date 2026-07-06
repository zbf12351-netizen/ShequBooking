// pages/feedback/feedback.js
const app = getApp()

Page({
  data: {
    feedbackTypes: [
      { value: 'consultation', label: '咨询' },
      { value: 'complaint', label: '投诉' },
      { value: 'suggestion', label: '建议' }
    ],
    typeIndex: 0,
    content: ''
  },

  onLoad() {
    if (!app.checkLogin()) return
  },

  onTypeChange(e) {
    this.setData({
      typeIndex: e.detail.value
    })
  },

  onContentInput(e) {
    this.setData({
      content: e.detail.value
    })
  },

  async handleSubmit() {
    if (!this.data.content.trim()) {
      wx.showToast({
        title: '请输入反馈内容',
        icon: 'none'
      })
      return
    }

    wx.showLoading({ title: '提交中...' })

    try {
      const res = await app.request({
        url: '/feedback/create',
        method: 'POST',
        data: {
          type: this.data.feedbackTypes[this.data.typeIndex].value,
          content: this.data.content
        }
      })

      wx.hideLoading()

      if (res.code === 200) {
        wx.showToast({
          title: '提交成功',
          icon: 'success'
        })

        setTimeout(() => {
          wx.navigateBack()
        }, 1500)
      } else {
        wx.showToast({
          title: res.message || '提交失败',
          icon: 'none'
        })
      }
    } catch (error) {
      wx.hideLoading()
      wx.showToast({
        title: '提交失败',
        icon: 'none'
      })
    }
  }
})

