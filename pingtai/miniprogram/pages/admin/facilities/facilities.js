// pages/admin/facilities/facilities.js
const app = getApp()

Page({
  data: {
    facilities: [],
    page: 1,
    pageSize: 20,
    total: 0,
    loading: false,
    editingId: null,
    // 筛选相关
    categoryList: ['全部', '运动设施', '会议场所', '活动场所', '文化设施'],
    categoryOptions: ['运动设施', '会议场所', '活动场所', '文化设施'],
    selectedCategoryIndex: 0,
    selectedCategory: '全部',
    // 表单
    form: {
      name: '',
      category: '',
      location: '',
      description: '',
      capacity: 1,
      status: 1,
      image_url: '',
      // 签到设置
      latitude: '',
      longitude: '',
      checkin_radius: 200,
      require_checkin_location: true
    }
  },

  onLoad() {
    if (!app.checkLogin()) return
    this.loadFacilities(true)
    this.loadCategories()
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

  async loadCategories() {
    try {
      const res = await app.request({
        url: '/admin/facilities/categories'
      })
      if (res.code === 200) {
        const categories = (res.data || []).map(item => item.category)
        this.setData({
          categoryList: ['全部', ...categories],
          categoryOptions: categories.length > 0 ? categories : ['运动设施', '会议场所', '活动场所', '文化设施']
        })
      }
    } catch (error) {
      console.error('加载分类失败', error)
    }
  },

  // 类别选择变化
  onCategoryChange(e) {
    const index = parseInt(e.detail.value, 10)
    const category = this.data.categoryOptions[index]
    this.setData({
      selectedCategoryIndex: index,
      'form.category': category
    })
  },

  onCategoryTap(e) {
    const category = e.currentTarget.dataset.category
    this.setData({ selectedCategory: category })
    this.loadFacilities(true)
  },

  async loadFacilities(reset = false) {
    if (this.data.loading) return
    
    // 如果是加载更多但已经加载完了
    if (!reset && this.data.facilities.length >= this.data.total) {
      return
    }
    
    this.setData({ loading: true })
    const page = reset ? 1 : this.data.page + 1
    
    // 构建请求参数
    const data = {
      page,
      page_size: this.data.pageSize
    }
    
    // 添加分类筛选
    if (this.data.selectedCategory !== '全部') {
      data.category = this.data.selectedCategory
    }
    
    try {
      const res = await app.request({
        url: '/admin/facilities/list',
        data
      })
      if (res.code === 200) {
        let newList = res.data.facilities
        if (!reset) {
          // 加载更多，追加数据
          newList = [...this.data.facilities, ...newList]
        }
        this.setData({
          facilities: newList,
          total: res.data.total,
          page,
          loading: false
        })
      } else {
        this.setData({ loading: false })
        wx.showToast({ title: res.message || '加载失败', icon: 'none' })
      }
    } catch (error) {
      this.setData({ loading: false })
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },

  onInput(e) {
    const { field } = e.currentTarget.dataset
    this.setData({ [`form.${field}`]: e.detail.value })
  },

  onNumberInput(e) {
    const { field } = e.currentTarget.dataset
    const value = parseInt(e.detail.value || '0', 10)
    this.setData({ [`form.${field}`]: value })
  },

  onStatusChange(e) {
    // range是['启用', '停用']，索引0对应启用(status=1)，索引1对应停用(status=0)
    const status = e.detail.value == 0 ? 1 : 0
    this.setData({ 'form.status': status })
  },

  resetForm() {
    this.setData({
      editingId: null,
      form: {
        name: '',
        category: '',
        location: '',
        description: '',
        capacity: 1,
        status: 1,
        image_url: '',
        // 签到设置 - 默认无需位置验证
        latitude: '',
        longitude: '',
        checkin_radius: 200,
        require_checkin_location: false
      }
    })
  },

  // 切换是否需要位置签到
  onRequireLocationChange(e) {
    // picker 返回选中项的索引（字符串类型）：'0'=需要位置验证，'1'=无需位置验证
    const value = e.detail.value === '0'  // 与字符串 '0' 比较
    this.setData({
      'form.require_checkin_location': value
    })
  },

  // 获取当前位置作为设施位置
  getLocation() {
    wx.showLoading({ title: '获取位置中...' })
    wx.getLocation({
      type: 'gcj02',
      success: (res) => {
        wx.hideLoading()
        this.setData({
          'form.latitude': res.latitude.toFixed(6),
          'form.longitude': res.longitude.toFixed(6)
        })
        wx.showToast({ title: '已获取位置', icon: 'success' })
      },
      fail: (err) => {
        wx.hideLoading()
        wx.showToast({ title: '获取位置失败', icon: 'none' })
        console.error('获取位置失败:', err)
      }
    })
  },

  editFacility(e) {
    const id = e.currentTarget.dataset.id
    const target = this.data.facilities.find(f => f.facility_id === id)
    if (!target) return
    // 确保 require_checkin_location 是布尔值，默认 false
    const requireCheckin = target.require_checkin_location === true
    // 找到类别对应的索引
    const categoryIndex = this.data.categoryOptions.indexOf(target.category)
    this.setData({
      editingId: id,
      selectedCategoryIndex: categoryIndex >= 0 ? categoryIndex : 0,
      form: {
        name: target.name,
        category: target.category,
        location: target.location,
        description: target.description || '',
        capacity: target.capacity || 1,
        status: target.status,
        image_url: target.image_url || '',
        // 签到设置
        latitude: target.latitude || '',
        longitude: target.longitude || '',
        checkin_radius: target.checkin_radius || 200,
        require_checkin_location: requireCheckin || false  // 修复：确保是布尔值
      }
    })
  },

  async submitFacility() {
    const { form, editingId } = this.data
    if (!form.name || !form.category || !form.location) {
      wx.showToast({ title: '请填写必填项', icon: 'none' })
      return
    }
    wx.showLoading({ title: editingId ? '更新中...' : '创建中...' })
    try {
      const url = editingId ? `/admin/facilities/update/${editingId}` : '/admin/facilities/create'
      const method = editingId ? 'PUT' : 'POST'
      const res = await app.request({
        url,
        method,
        data: {
          ...form
        }
      })
      wx.hideLoading()
      if (res.code === 200) {
        wx.showToast({ title: editingId ? '已更新' : '已创建', icon: 'success' })
        this.resetForm()
        this.loadFacilities(true)
      } else {
        wx.showToast({ title: res.message || '提交失败', icon: 'none' })
      }
    } catch (error) {
      wx.hideLoading()
      wx.showToast({ title: '提交失败', icon: 'none' })
    }
  },

  async deleteFacility(e) {
    const { id } = e.currentTarget.dataset
    wx.showModal({
      title: '确认删除',
      content: '删除后不可恢复，是否继续？',
      success: async (res) => {
        if (!res.confirm) return
        wx.showLoading({ title: '删除中...' })
        try {
          const result = await app.request({
            url: `/admin/facilities/delete/${id}`,
            method: 'DELETE'
          })
          wx.hideLoading()
          if (result.code === 200) {
            wx.showToast({ title: '已删除', icon: 'success' })
            this.loadFacilities(true)
          } else {
            wx.showToast({ title: result.message || '删除失败', icon: 'none' })
          }
        } catch (error) {
          wx.hideLoading()
          wx.showToast({ title: '删除失败', icon: 'none' })
        }
      }
    })
  },

  // 选择图片
  chooseImage() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const tempFilePath = res.tempFiles[0].tempFilePath
        this.uploadImage(tempFilePath)
      }
    })
  },

  // 上传图片
  uploadImage(filePath) {
    console.log('开始上传图片:', filePath)
    console.log('上传URL:', app.globalData.baseUrl + '/admin/upload/image')
    console.log('Token:', app.globalData.token)
    
    wx.showLoading({ title: '上传中...' })
    wx.uploadFile({
      url: app.globalData.baseUrl + '/admin/upload/image',
      filePath: filePath,
      name: 'file',
      header: {
        'Authorization': 'Bearer ' + wx.getStorageSync('token')
      },
      success: (res) => {
        console.log('上传响应状态码:', res.statusCode)
        console.log('上传响应内容:', res.data)
        wx.hideLoading()
        try {
          const data = JSON.parse(res.data)
          console.log('解析后的数据:', data)
          if (data.code === 200) {
            // 后端返回完整URL，直接使用
            this.setData({
              'form.image_url': data.data.url
            })
            wx.showToast({ title: '上传成功', icon: 'success' })
          } else {
            wx.showToast({ title: data.message || '上传失败', icon: 'none' })
          }
        } catch (e) {
          console.error('JSON解析失败:', e)
          wx.showToast({ title: '响应解析失败', icon: 'none' })
        }
      },
      fail: (err) => {
        console.error('上传请求失败:', err)
        wx.hideLoading()
        wx.showToast({ title: '上传失败', icon: 'none' })
      }
    })
  },

  // 删除图片
  removeImage() {
    this.setData({
      'form.image_url': ''
    })
  },

  loadMore() {
    this.loadFacilities(false)
  }
})

