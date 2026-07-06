// pages/facility-detail/facility-detail.js
const app = getApp()

Page({
  data: {
    facilityId: null,
    facility: {},
    isFavorite: false,
    reviews: [],
    reviewPage: 1,
    reviewPageSize: 5,
    hasMoreReviews: true,
    reviewLoading: false,
    isLoggedIn: false
  },

  onLoad(options) {
    // 允许未登录查看设施详情
    if (options.id) {
      this.setData({
        facilityId: options.id
      })
      this.loadFacilityDetail()
    }
    
    // 检查登录状态
    this.checkLoginStatus()
  },

  onShow() {
    // 如果已加载过详情，只刷新收藏状态
    if (this.data.facilityId) {
      // 刷新评价列表
      this.setData({ reviewPage: 1 })
      this.loadReviews()
      // 刷新收藏状态（如果已登录）
      if (app.globalData.token) {
        this.loadFavoriteStatus()
      }
    }
    // 检查登录状态变化
    this.checkLoginStatus()
  },

  // 检查登录状态
  checkLoginStatus() {
    const isLoggedIn = !!app.globalData.token
    if (isLoggedIn !== this.data.isLoggedIn) {
      this.setData({ isLoggedIn })
      // 如果已登录，刷新收藏状态
      if (isLoggedIn) {
        this.loadFavoriteStatus()
      }
    }
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.loadFacilityDetail().finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  async loadFacilityDetail() {
    try {
      const res = await app.request({
        url: `/facility/detail/${this.data.facilityId}?review_page=1&review_page_size=${this.data.reviewPageSize}`
      })
      
      if (res.code === 200) {
        this.setData({
          facility: res.data,
          isFavorite: !!res.data.is_favorite,
          reviews: res.data.reviews?.items || [],
          hasMoreReviews: (res.data.reviews?.total || 0) > this.data.reviewPageSize
        })
      } else {
        wx.showToast({
          title: res.message || '加载失败',
          icon: 'none'
        })
      }
    } catch (error) {
      wx.showToast({
        title: '加载失败',
        icon: 'none'
      })
    }
  },

  // 加载收藏状态
  async loadFavoriteStatus() {
    if (!app.globalData.token) return
    
    try {
      const res = await app.request({
        url: `/facility/favorite/status/${this.data.facilityId}`,
        method: 'GET'
      })
      
      if (res.code === 200 && res.data) {
        this.setData({ isFavorite: !!res.data.is_favorite })
      }
    } catch (error) {
      // 请求失败时不要改变收藏状态
      console.error('获取收藏状态失败', error)
    }
  },

  async loadReviews() {
    if (this.data.reviewLoading) return
    
    this.setData({ reviewLoading: true })
    
    try {
      const res = await app.request({
        url: `/facility/detail/${this.data.facilityId}?review_page=${this.data.reviewPage}&review_page_size=${this.data.reviewPageSize}`
      })
      
      if (res.code === 200) {
        const newReviews = res.data.reviews?.items || []
        this.setData({
          reviews: this.data.reviewPage === 1 ? newReviews : [...this.data.reviews, ...newReviews],
          hasMoreReviews: (res.data.reviews?.total || 0) > (this.data.reviewPage * this.data.reviewPageSize)
        })
      }
    } catch (error) {
      console.error('加载评价失败', error)
    } finally {
      this.setData({ reviewLoading: false })
    }
  },

  // 加载更多评价
  loadMoreReviews() {
    if (!this.data.hasMoreReviews || this.data.reviewLoading) return
    
    const newPage = this.data.reviewPage + 1
    this.setData({ reviewPage: newPage })
    this.loadReviews()
  },

  goToBooking() {
    // 需要登录才能预约
    app.requireLogin(() => {
      wx.navigateTo({
        url: `/pages/booking/booking?facilityId=${this.data.facilityId}`
      })
    })
  },

  async toggleFavorite() {
    // 需要登录才能收藏
    if (!app.requireLogin()) return
    
    const { facilityId, isFavorite } = this.data
    const method = isFavorite ? 'DELETE' : 'POST'
    const loadingText = isFavorite ? '取消收藏...' : '收藏中...'
    wx.showLoading({ title: loadingText })

    try {
      const res = await app.request({
        url: `/facility/favorite/${facilityId}`,
        method
      })
      wx.hideLoading()
      if (res.code === 200 || res.code === 201) {
        this.setData({ isFavorite: !isFavorite })
        wx.showToast({
          title: isFavorite ? '已取消' : '已收藏',
          icon: 'success'
        })
        // 通知收藏列表页面刷新
        this.notifyFavoriteListRefresh(facilityId, !isFavorite)
      } else {
        wx.showToast({
          title: res.message || '操作失败',
          icon: 'none'
        })
      }
    } catch (error) {
      wx.hideLoading()
      wx.showToast({
        title: '操作失败',
        icon: 'none'
      })
    }
  },

  // 通知收藏列表页面刷新
  notifyFavoriteListRefresh(facilityId, isFavorite) {
    const pages = getCurrentPages()
    for (let i = 0; i < pages.length; i++) {
      if (pages[i].route === 'pages/favorite-list/favorite-list') {
        if (pages[i].refreshFavoriteStatus) {
          pages[i].refreshFavoriteStatus(facilityId, isFavorite)
        }
        break
      }
    }
  }
})

