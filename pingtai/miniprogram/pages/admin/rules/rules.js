// pages/admin/rules/rules.js
const app = getApp()

Page({
  data: {
    rules: [],
    facilities: [],
    facilityOptions: ['全局规则'],
    loading: false,
    editingId: null,
    facilityIndex: 0,
    selectedFacilityName: '全局规则',
    form: {
      rule_name: '',
      facility_id: '',
      max_advance_days: 7,
      min_duration: 30,
      max_duration: 120,
      daily_limit: 1,
      start_time: '08:00',
      end_time: '22:00',
      status: 1
    }
  },

  onLoad() {
    if (!app.checkLogin()) return
    this.loadFacilities()
    this.loadRules()
  },

  async loadFacilities() {
    try {
      const res = await app.request({
        url: '/admin/facilities/list',
        data: { page: 1, page_size: 200 }
      })
      if (res.code === 200) {
        const list = res.data.facilities || []
        this.setData({
          facilities: list,
          facilityOptions: ['全局规则'].concat(list.map(f => f.name))
        })
      }
    } catch (error) {
      console.error('加载设施列表失败', error)
    }
  },

  async loadRules() {
    this.setData({ loading: true })
    try {
      const res = await app.request({ url: '/admin/rules/list' })
      this.setData({ loading: false })
      if (res.code === 200) {
        this.setData({ rules: res.data })
      } else {
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

  onFacilityChange(e) {
    const index = Number(e.detail.value)
    let facilityId = ''
    let facilityName = '全局规则'
    if (index > 0) {
      const facility = this.data.facilities[index - 1]
      facilityId = facility ? facility.facility_id : ''
      facilityName = facility ? facility.name : '全局规则'
    }
    this.setData({
      facilityIndex: index,
      selectedFacilityName: facilityName,
      'form.facility_id': facilityId
    })
  },

  onStatusChange(e) {
    // range 是 ['启用', '停用']，索引 0 = 启用(status=1)，索引 1 = 停用(status=0)
    const status = e.detail.value == 0 ? 1 : 0
    this.setData({ 'form.status': status })
  },

  resetForm() {
    this.setData({
      editingId: null,
      facilityIndex: 0,
      selectedFacilityName: '全局规则',
      form: {
        rule_name: '',
        facility_id: '',
        max_advance_days: 7,
        min_duration: 30,
        max_duration: 120,
        daily_limit: 1,
        start_time: '08:00',
        end_time: '22:00',
        status: 1
      }
    })
  },

  editRule(e) {
    const id = e.currentTarget.dataset.id
    const target = this.data.rules.find(r => r.rule_id === id)
    if (!target) return
    // 计算 picker 位置与显示名
    let facilityIndex = 0
    let selectedName = '全局规则'
    if (target.facility_id) {
      const idx = this.data.facilities.findIndex(f => f.facility_id === target.facility_id)
      if (idx >= 0) {
        facilityIndex = idx + 1
        selectedName = this.data.facilities[idx].name
      } else {
        selectedName = String(target.facility_id)
      }
    }
    this.setData({
      editingId: id,
      facilityIndex,
      selectedFacilityName: selectedName,
      form: {
        rule_name: target.rule_name,
        facility_id: target.facility_id || '',
        max_advance_days: target.max_advance_days,
        min_duration: target.min_duration,
        max_duration: target.max_duration,
        daily_limit: target.daily_limit,
        start_time: target.start_time,
        end_time: target.end_time,
        status: target.status
      }
    })
  },

  async submitRule() {
    const { form, editingId } = this.data
    if (!form.rule_name) {
      wx.showToast({ title: '请填写规则名称', icon: 'none' })
      return
    }
    const payload = { ...form }
    if (payload.facility_id === '') payload.facility_id = null

    wx.showLoading({ title: editingId ? '更新中...' : '创建中...' })
    try {
      const url = editingId ? `/admin/rules/update/${editingId}` : '/admin/rules/create'
      const method = editingId ? 'PUT' : 'POST'
      const res = await app.request({ url, method, data: payload })
      wx.hideLoading()
      if (res.code === 200) {
        wx.showToast({ title: editingId ? '已更新' : '已创建', icon: 'success' })
        this.resetForm()
        this.loadRules()
      } else {
        wx.showToast({ title: res.message || '提交失败', icon: 'none' })
      }
    } catch (error) {
      wx.hideLoading()
      wx.showToast({ title: '提交失败', icon: 'none' })
    }
  },

  async deleteRule(e) {
    const id = e.currentTarget.dataset.id
    const target = this.data.rules.find(r => r.rule_id === id)
    if (!target) return

    wx.showModal({
      title: '确认删除',
      content: `确定要删除规则"${target.rule_name}"吗？`,
      success: async (res) => {
        if (res.confirm) {
          wx.showLoading({ title: '删除中...' })
          try {
            const result = await app.request({
              url: `/admin/rules/delete/${id}`,
              method: 'DELETE'
            })
            wx.hideLoading()
            if (result.code === 200) {
              wx.showToast({ title: '已删除', icon: 'success' })
              this.loadRules()
            } else {
              wx.showToast({ title: result.message || '删除失败', icon: 'none' })
            }
          } catch (error) {
            wx.hideLoading()
            wx.showToast({ title: '删除失败', icon: 'none' })
          }
        }
      }
    })
  }
})

