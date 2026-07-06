// pages/booking/booking.js
const app = getApp()

Page({
  data: {
    facilities: [],
    facilityIndex: 0,
    selectedFacility: null,
    bookingDate: '',
    startTime: '',
    endTime: '',
    purpose: '',
    minDate: '',
    maxDate: '',
    recommendedTimes: [],
    selectedTime: ''
  },

  onLoad(options) {
    if (!app.checkLogin()) return
    
    // 设置日期范围（今天到7天后）
    const today = new Date()
    const maxDate = new Date()
    maxDate.setDate(maxDate.getDate() + 7)
    
    // 获取当前时间，设置为默认时间
    const hours = String(today.getHours()).padStart(2, '0')
    const minutes = String(today.getMinutes()).padStart(2, '0')
    const currentTime = `${hours}:${minutes}`
    
    // 默认结束时间为开始时间后1小时
    let endHour = today.getHours() + 1
    if (endHour > 23) endHour = 23
    const endTime = `${String(endHour).padStart(2, '0')}:${minutes}`
    
    // 默认选择今天
    const todayStr = this.formatDate(today)
    
    this.setData({
      minDate: this.formatDate(today),
      maxDate: this.formatDate(maxDate),
      bookingDate: todayStr,
      startTime: currentTime,
      endTime: endTime
    })
    
    this.loadFacilities()
    
    // 如果从详情页跳转过来，自动选择设施
    if (options.facilityId) {
      this.preSelectFacility(options.facilityId)
    } else {
      // 如果没有预选设施，先加载推荐时间（使用默认日期）
      setTimeout(() => {
        if (this.data.selectedFacility) {
          this.loadRecommendedTimes()
        }
      }, 500)
    }
  },

  formatDate(date) {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  },

  async loadFacilities() {
    try {
      const res = await app.request({
        url: '/facility/list?page_size=100'
      })
      
      if (res.code === 200) {
        this.setData({
          facilities: res.data.facilities
        })
        // 设施加载成功后，如果已经有默认日期，自动加载推荐时间
        if (this.data.bookingDate && !this.data.selectedFacility && res.data.facilities.length > 0) {
          this.setData({
            selectedFacility: res.data.facilities[0],
            facilityIndex: 0
          })
          this.loadRecommendedTimes()
        }
      }
    } catch (error) {
      console.error('加载设施失败', error)
    }
  },

  preSelectFacility(facilityId) {
    setTimeout(() => {
      const index = this.data.facilities.findIndex(f => f.facility_id == facilityId)
      if (index !== -1) {
        this.setData({
          facilityIndex: index,
          selectedFacility: this.data.facilities[index]
        })
        // 预选设施后自动加载推荐时间
        if (this.data.bookingDate) {
          this.loadRecommendedTimes()
        }
      }
    }, 500)
  },

  onFacilityChange(e) {
    const index = e.detail.value
    const selectedFacility = this.data.facilities[index]
    this.setData({
      facilityIndex: index,
      selectedFacility: selectedFacility,
      recommendedTimes: []
    })
    
    // 选择设施后自动加载推荐时间
    if (selectedFacility && this.data.bookingDate) {
      this.loadRecommendedTimes()
    }
  },

  onDateChange(e) {
    this.setData({
      bookingDate: e.detail.value,
      recommendedTimes: []
    })
    
    // 自动加载推荐时间
    if (this.data.selectedFacility) {
      this.loadRecommendedTimes()
    }
  },

  onStartTimeChange(e) {
    this.setData({
      startTime: e.detail.value,
      selectedTime: ''
    })
    // 自动加载推荐时间
    this.loadRecommendedTimes()
  },

  onEndTimeChange(e) {
    this.setData({
      endTime: e.detail.value
    })
  },

  onPurposeInput(e) {
    this.setData({
      purpose: e.detail.value
    })
  },

  // 加载推荐时间段
  async loadRecommendedTimes() {
    if (!this.data.selectedFacility || !this.data.bookingDate) return
    
    // 计算实际预约时长
    const startParts = this.data.startTime.split(':').map(Number)
    const endParts = this.data.endTime.split(':').map(Number)
    const duration = (endParts[0] * 60 + endParts[1]) - (startParts[0] * 60 + startParts[1])
    
    try {
      const res = await app.request({
        url: '/booking/suggest-time',
        data: {
          facility_id: this.data.selectedFacility.facility_id,
          date: this.data.bookingDate,
          duration: duration,
          preferred_start: this.data.startTime  // 传用户选择的开始时间
        }
      })
      
      if (res.code === 200) {
        this.setData({
          recommendedTimes: res.data
        })
      }
    } catch (error) {
      console.error('加载推荐时间失败', error)
    }
  },

  // 选择推荐时间
  selectRecommendedTime(e) {
    const { start, end } = e.currentTarget.dataset
    this.setData({
      startTime: start,
      endTime: end,
      selectedTime: start + '-' + end
    })
  },

  // 刷新推荐
  refreshRecommendations() {
    this.loadRecommendedTimes()
  },

  // 验证表单
  validateForm() {
    if (!this.data.selectedFacility) {
      wx.showToast({ title: '请选择设施', icon: 'none' })
      return false
    }
    
    if (!this.data.bookingDate) {
      wx.showToast({ title: '请选择日期', icon: 'none' })
      return false
    }
    
    if (!this.data.startTime) {
      wx.showToast({ title: '请选择开始时间', icon: 'none' })
      return false
    }
    
    if (!this.data.endTime) {
      wx.showToast({ title: '请选择结束时间', icon: 'none' })
      return false
    }
    
    // 时间比较（字符串比较对HH:MM格式有效）
    if (this.data.startTime >= this.data.endTime) {
      wx.showToast({ title: '结束时间必须大于开始时间', icon: 'none' })
      return false
    }

    // 验证预约时长不超过4小时
    const startParts = this.data.startTime.split(':').map(Number)
    const endParts = this.data.endTime.split(':').map(Number)
    const startMinutes = startParts[0] * 60 + startParts[1]
    const endMinutes = endParts[0] * 60 + endParts[1]
    const duration = endMinutes - startMinutes

    if (duration > 240) {
      wx.showToast({ title: '预约时长不能超过4小时', icon: 'none' })
      return false
    }
    
    return true
  },

  // 保存草稿
  async handleSave() {
    if (!this.validateForm()) return
    
    await this.submitBooking(true)
  },

  // 提交审核
  async handleSubmit() {
    if (!this.validateForm()) return
    
    await this.submitBooking(false)
  },

  async submitBooking(isDraft) {
    wx.showLoading({ title: isDraft ? '保存中...' : '提交中...' })
    
    try {
      const res = await app.request({
        url: '/booking/create',
        method: 'POST',
        data: {
          facility_id: this.data.selectedFacility.facility_id,
          booking_date: this.data.bookingDate,
          start_time: this.data.startTime,
          end_time: this.data.endTime,
          purpose: this.data.purpose,
          is_draft: isDraft
        }
      })
      
      wx.hideLoading()
      
      if (res.code === 200) {
        wx.showToast({
          title: isDraft ? '保存成功' : '提交成功',
          icon: 'success'
        })
        
        setTimeout(() => {
          wx.navigateBack()
        }, 1500)
      } else {
        wx.showToast({
          title: res.message || '操作失败',
          icon: 'none'
        })
      }
    } catch (error) {
      wx.hideLoading()
      wx.showToast({
        title: error.message || '操作失败',
        icon: 'none'
      })
    }
  }
})

