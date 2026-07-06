// pages/facilities/facilities.js
const app = getApp()

Page({
  data: {
    keyword: '',
    activeCategory: '',
    categories: [],
    facilities: [],
    page: 1,
    pageSize: 10,
    hasMore: true,
    loading: false,
    isLoggedIn: false,
    tabBarConfig: []
  },

  onLoad() {
    // 从全局获取 TabBar 配置
    this.setData({
      tabBarConfig: app.globalData.tabBarConfig
    })
    
    // 允许未登录查看设施列表
    this.checkLoginStatus()
    this.loadCategories()
    this.loadFacilities()
  },

  onTabChange(e) {
    const { path } = e.detail
    if (path) {
      wx.switchTab({ url: '/' + path })
    }
  },

  onShow() {
    // 页面显示时刷新设施列表（更新收藏状态等）
    this.checkLoginStatus()
    this.loadFacilities(true)
  },

  // 检查登录状态
  checkLoginStatus() {
    const isLoggedIn = !!app.globalData.token
    if (isLoggedIn !== this.data.isLoggedIn) {
      this.setData({ isLoggedIn })
    }
  },

  // 下拉刷新
  onPullDownRefresh() {
    // 并行加载类别和设施列表
    Promise.allSettled([
      this.loadCategories(),
      this.loadFacilities(true)
    ]).finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  // 加载类别列表
  async loadCategories() {
    try {
      const res = await app.request({
        url: '/facility/categories'
      })
      
      if (res.code === 200) {
        this.setData({
          categories: res.data
        })
      }
    } catch (error) {
      console.error('加载类别失败', error)
    }
  },

  // 加载设施列表
  async loadFacilities(reset = false) {
    if (this.data.loading) return
    
    this.setData({ loading: true })
    
    const page = reset ? 1 : this.data.page
    
    try {
      const res = await app.request({
        url: '/facility/list',
        data: {
          page,
          page_size: this.data.pageSize,
          category: this.data.activeCategory,
          keyword: this.data.keyword
        }
      })
      
      if (res.code === 200) {
        console.log('=== 设施列表返回数据 ===')
        console.log('总数:', res.data.total)
        console.log('设施列表:', JSON.stringify(res.data.facilities, null, 2))
        
        const newFacilities = reset ? res.data.facilities : [...this.data.facilities, ...res.data.facilities]
        
        this.setData({
          facilities: newFacilities,
          page: page,
          hasMore: newFacilities.length >= this.data.pageSize && (page * this.data.pageSize) < res.data.total,
          loading: false
        })
      }
    } catch (error) {
      console.error('加载设施失败', error)
      this.setData({ loading: false })
    }
  },

  // 搜索
  onKeywordInput(e) {
    this.setData({
      keyword: e.detail.value
    })
  },

  handleSearch() {
    this.loadFacilities(true)
  },

  // 切换类别
  onCategoryChange(e) {
    const category = e.currentTarget.dataset.category
    
    this.setData({
      activeCategory: category,
      page: 1
    })
    
    this.loadFacilities(true)
  },

  // 加载更多
  loadMore() {
    if (this.data.hasMore && !this.data.loading) {
      this.setData({
        page: this.data.page + 1
      })
      this.loadFacilities()
    }
  },

  // 跳转详情
  goToDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `/pages/facility-detail/facility-detail?id=${id}`
    })
  },

  // 接收收藏列表页面发来的状态更新
  refreshFavoriteStatus(facilityId, isFavorite) {
    const facilities = this.data.facilities
    for (let i = 0; i < facilities.length; i++) {
      if (facilities[i].facility_id === facilityId) {
        facilities[i].is_favorite = isFavorite
        // 使用新数组方式更新，确保视图刷新
        const newFacilities = [...this.data.facilities]
        newFacilities[i] = {
          ...newFacilities[i],
          is_favorite: isFavorite
        }
        this.setData({ facilities: newFacilities })
        break
      }
    }
  },

  async toggleFavorite(e) {
    // 需要登录才能收藏
    if (!app.requireLogin()) return
    
    const { id, index } = e.currentTarget.dataset
    const target = this.data.facilities[index]
    if (!target) return

    const isFavorite = !!target.is_favorite
    const method = isFavorite ? 'DELETE' : 'POST'
    console.log('=== 收藏操作 ===')
    console.log('facilityId:', id)
    console.log('当前状态:', isFavorite)
    console.log('请求方法:', method)
    console.log('Token:', app.globalData.token ? '已存在' : '不存在')
    
    wx.showLoading({ title: isFavorite ? '取消收藏...' : '收藏中...' })

    try {
      const res = await app.request({
        url: `/facility/favorite/${id}`,
        method
      })
      wx.hideLoading()
      console.log('收藏响应:', res)
      if (res.code === 200 || res.code === 201) {
        // 使用新数组方式更新，确保视图刷新
        const newFacilities = [...this.data.facilities]
        newFacilities[index] = {
          ...newFacilities[index],
          is_favorite: !isFavorite
        }
        this.setData({ facilities: newFacilities })
        wx.showToast({
          title: isFavorite ? '已取消' : '已收藏',
          icon: 'success'
        })
      } else {
        wx.showToast({
          title: res.message || '操作失败',
          icon: 'none'
        })
      }
    } catch (error) {
      wx.hideLoading()
      console.error('收藏错误:', error)
      wx.showToast({
        title: '操作失败',
        icon: 'none'
      })
    }
  }
})

