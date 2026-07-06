// pages/home/home.js
const app = getApp()

Page({
  data: {
    userInfo: null,
    isLoggedIn: false,
    recommendList: [],
    popularList: [],
    announcements: [],
    isRefreshing: false,  // 下拉刷新状态
    tabBarConfig: []
  },

  onLoad() {
    // 从全局获取 TabBar 配置
    this.setData({
      tabBarConfig: app.globalData.tabBarConfig
    })
    
    // 无论是否登录都加载首页
    this.loadPublicData()
    
    // 如果已登录，加载个性化推荐
    if (app.globalData.token) {
      this.setData({
        isLoggedIn: true,
        userInfo: app.globalData.userInfo
      })
      this.loadRecommendFacilities()
    }
  },

  // 加载公开数据（公告 + 热门设施）
  async loadPublicData() {
    try {
      // 使用 Promise.allSettled 确保即使一个请求失败，另一个也能完成
      const results = await Promise.allSettled([
        new Promise((resolve, reject) => {
          wx.request({
            url: app.globalData.baseUrl + '/notification/public/announcements?page=1&page_size=5',
            method: 'GET',
            success: resolve,
            fail: reject
          })
        }),
        app.request({
          url: '/facility/popular?limit=8'
        })
      ])

      // 处理公告结果
      const announcementsResult = results[0]
      if (announcementsResult.status === 'fulfilled' && announcementsResult.value.data.code === 200) {
        this.setData({
          announcements: announcementsResult.value.data.data.announcements || []
        })
      }

      // 处理热门设施结果
      const popularResult = results[1]
      if (popularResult.status === 'fulfilled' && popularResult.value.code === 200) {
        this.setData({
          popularList: popularResult.value.data
        })
      }
    } catch (error) {
      console.error('加载公开数据失败', error)
    }
  },

  onTabChange(e) {
    const { path } = e.detail
    if (path) {
      wx.switchTab({ url: '/' + path })
    }
  },

  onShow() {
    // 检查登录状态变化
    const isLoggedIn = !!app.globalData.token
    const userInfo = app.globalData.userInfo
    
    if (isLoggedIn !== this.data.isLoggedIn || 
        JSON.stringify(userInfo) !== JSON.stringify(this.data.userInfo)) {
      this.setData({
        isLoggedIn,
        userInfo
      })
      
      // 如果刚刚登录，加载推荐设施
      if (isLoggedIn && this.data.recommendList.length === 0) {
        this.loadRecommendFacilities()
      }
    }
    
    // 如果已登录且有推荐数据，刷新推荐状态
    if (isLoggedIn && this.data.recommendList.length > 0) {
      this.loadRecommendFacilities()
    }
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.setData({ isRefreshing: true })
    // 并行加载所有数据，使用 Promise.allSettled 等待全部完成
    const loadPromises = [
      this.loadAnnouncements(),
      this.loadPopularFacilities()
    ]
    
    // 如果已登录，也加载推荐设施
    if (this.data.isLoggedIn) {
      loadPromises.push(this.loadRecommendFacilities())
    }
    
    Promise.allSettled(loadPromises).finally(() => {
      this.setData({ isRefreshing: false })
      wx.stopPullDownRefresh()
    })
  },

  // 加载公告（公开API，无需登录）
  async loadAnnouncements() {
    try {
      const res = await new Promise((resolve, reject) => {
        wx.request({
          url: app.globalData.baseUrl + '/notification/public/announcements?page=1&page_size=5',
          method: 'GET',
          success: resolve,
          fail: reject
        })
      })
      
      if (res.data.code === 200) {
        this.setData({
          announcements: res.data.data.announcements || []
        })
      }
    } catch (error) {
      console.error('加载公告失败', error)
    }
  },

  // 加载推荐设施（需要登录）
  async loadRecommendFacilities() {
    if (!app.globalData.token) return
    
    try {
      const res = await app.request({
        url: '/facility/recommend?limit=3'
      })
      
      if (res.code === 200) {
        this.setData({
          recommendList: res.data
        })
      }
    } catch (error) {
      console.error('加载推荐设施失败', error)
    }
  },

  // 加载热门设施（公开API，无需登录）
  async loadPopularFacilities() {
    try {
      const res = await app.request({
        url: '/facility/popular?limit=8'
      })
      
      if (res.code === 200) {
        this.setData({
          popularList: res.data
        })
      }
    } catch (error) {
      console.error('加载热门设施失败', error)
    }
  },

  // 跳转到设施详情
  goToDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `/pages/facility-detail/facility-detail?id=${id}`
    })
  },

  // 快捷功能导航
  goToFacilities() {
    wx.switchTab({
      url: '/pages/facilities/facilities'
    })
  },

  goToBooking() {
    wx.switchTab({
      url: '/pages/facilities/facilities'
    })
  },

  goToMyBookings() {
    // 需要登录
    app.requireLogin(() => {
      wx.switchTab({
        url: '/pages/booking-list/booking-list'
      })
    })
  },

  goToFeedback() {
    // 需要登录
    app.requireLogin(() => {
      wx.navigateTo({
        url: '/pages/feedback-list/feedback-list'
      })
    })
  },

  goToRecommend() {
    if (!app.globalData.token) {
      wx.showModal({
        title: '提示',
        content: '登录后查看智能推荐',
        confirmText: '去登录',
        success: (res) => {
          if (res.confirm) {
            wx.redirectTo({
              url: '/pages/login/login'
            })
          }
        }
      })
      return
    }
    wx.switchTab({
      url: '/pages/facilities/facilities'
    })
  },

  goToPopular() {
    wx.switchTab({
      url: '/pages/facilities/facilities'
    })
  },

  // 跳转到公告详情
  goToAnnouncementDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `/pages/notification-detail/notification-detail?id=${id}`
    })
  },

  // 跳转到公告列表
  goToAnnouncementList() {
    wx.navigateTo({
      url: '/pages/notification-list/notification-list'
    })
  },

  // 去登录
  goToLogin() {
    wx.redirectTo({
      url: '/pages/login/login'
    })
  },

  // 去注册
  goToRegister() {
    wx.navigateTo({
      url: '/pages/register/register'
    })
  }
})
