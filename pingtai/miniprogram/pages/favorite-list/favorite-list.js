// pages/favorite-list/favorite-list.js
const app = getApp()

Page({
  data: {
    favorites: [],
    page: 1,
    pageSize: 10,
    hasMore: true,
    loading: false
  },

  onLoad() {
    if (!app.checkLogin()) return
    this.loadFavorites()
  },

  onShow() {
    // 每次页面显示时刷新列表
    this.loadFavorites(true)
  },

  onPullDownRefresh() {
    // 下拉刷新
    this.loadFavorites(true).finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  async loadFavorites(reset = false) {
    if (this.data.loading) return
    
    this.setData({ loading: true })

    const page = reset ? 1 : this.data.page
    try {
      const res = await app.request({
        url: '/facility/favorites',
        data: {
          page,
          page_size: this.data.pageSize
        }
      })

      if (res.code === 200) {
        const list = res.data.favorites || []
        this.setData({
          favorites: list,
          page,
          hasMore: list.length >= this.data.pageSize && (page * this.data.pageSize) < res.data.total,
          loading: false
        })
      } else {
        this.setData({ loading: false })
        wx.showToast({
          title: res.message || '加载失败',
          icon: 'none'
        })
      }
    } catch (error) {
      this.setData({ loading: false })
      wx.showToast({
        title: '加载失败',
        icon: 'none'
      })
    }
  },

  loadMore() {
    if (this.data.hasMore && !this.data.loading) {
      this.setData({ page: this.data.page + 1 })
      this.loadFavorites()
    }
  },

  goToDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `/pages/facility-detail/facility-detail?id=${id}`
    })
  },

  async removeFavorite(e) {
    const { id, index } = e.currentTarget.dataset
    wx.showLoading({ title: '取消收藏...' })
    try {
      const res = await app.request({
        url: `/facility/favorite/${id}`,
        method: 'DELETE'
      })
      wx.hideLoading()
      if (res.code === 200) {
        const list = [...this.data.favorites]
        list.splice(index, 1)
        this.setData({
          favorites: list
        })
        wx.showToast({ title: '已取消', icon: 'success' })
        // 通知设施列表页面刷新
        this.notifyFacilitiesRefresh(id)
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

  // 处理设施详情页面发来的收藏状态更新通知
  refreshFavoriteStatus(facilityId, isFavorite) {
    if (!isFavorite) {
      // 如果取消了收藏，从列表中移除
      const list = this.data.favorites.filter(item => item.facility_id !== facilityId)
      this.setData({
        favorites: list
      })
    }
  },

  // 通知设施列表页面刷新收藏状态
  notifyFacilitiesRefresh(facilityId) {
    const pages = getCurrentPages()
    for (let i = 0; i < pages.length; i++) {
      if (pages[i].route === 'pages/facilities/facilities') {
        if (pages[i].refreshFavoriteStatus) {
          pages[i].refreshFavoriteStatus(facilityId, false)
        }
        break
      }
    }
  }
})

