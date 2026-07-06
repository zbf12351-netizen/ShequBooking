// pages/admin/users/users.js
const app = getApp()

Page({
  data: {
    users: [],
    page: 1,
    pageSize: 100,  // 改为100，一次显示所有用户
    total: 0,
    roleFilter: 'all',
    loading: false,
    auditorPhone: '',
    auditorPassword: '',
    auditorName: '',
    auditorRole: 'auditor'
  },

  onLoad() {
    if (!app.checkLogin()) return
    this.loadUsers(true)
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.loadUsers(true).finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  async loadUsers(reset = false) {
    if (this.data.loading) return
    this.setData({ loading: true })
    const page = reset ? 1 : this.data.page
    try {
      const res = await app.request({
        url: '/admin/users/list',
        data: {
          page,
          page_size: this.data.pageSize,
          role: this.data.roleFilter
        }
      })
      if (res.code === 200) {
        this.setData({
          users: res.data.users,
          total: res.data.total,
          page,
          loading: false
        })
      } else {
        this.setData({ loading: false })
        wx.showToast({ title: res.message || '加载失败', icon: 'none' })
      }
    } catch (err) {
      this.setData({ loading: false })
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },

  onRoleChange(e) {
    const role = e.currentTarget.dataset.role
    this.setData({ roleFilter: role })
    this.loadUsers(true)
  },

  onInput(e) {
    const { field } = e.currentTarget.dataset
    this.setData({ [field]: e.detail.value })
  },

  onRoleSelect(e) {
    const role = e.currentTarget.dataset.role
    this.setData({ auditorRole: role })
  },

  async createUser() {
    const { auditorPhone, auditorPassword, auditorName, auditorRole } = this.data
    if (!auditorPhone || !auditorPassword || !auditorName) {
      wx.showToast({ title: '请完整填写用户信息', icon: 'none' })
      return
    }
    wx.showLoading({ title: '创建中...' })
    try {
      const res = await app.request({
        url: '/admin/users/create',
        method: 'POST',
        data: {
          phone: auditorPhone,
          password: auditorPassword,
          username: auditorName,
          role: auditorRole
        }
      })
      wx.hideLoading()
      if (res.code === 200) {
        wx.showToast({ title: '创建成功', icon: 'success' })
        this.setData({
          auditorPhone: '',
          auditorPassword: '',
          auditorName: ''
        })
        this.loadUsers(true)
      } else {
        wx.showToast({ title: res.message || '创建失败', icon: 'none' })
      }
    } catch (error) {
      wx.hideLoading()
      wx.showToast({ title: '创建失败', icon: 'none' })
    }
  },

  async toggleStatus(e) {
    const { id } = e.currentTarget.dataset
    wx.showLoading({ title: '操作中...' })
    try {
      const res = await app.request({
        url: `/admin/users/toggle-status/${id}`,
        method: 'POST'
      })
      wx.hideLoading()
      if (res.code === 200) {
        wx.showToast({ title: '已更新', icon: 'success' })
        this.loadUsers()
      } else {
        wx.showToast({ title: res.message || '操作失败', icon: 'none' })
      }
    } catch (error) {
      wx.hideLoading()
      wx.showToast({ title: '操作失败', icon: 'none' })
    }
  },

  async deleteUser(e) {
    const { id } = e.currentTarget.dataset
    wx.showModal({
      title: '确认删除',
      content: '删除后不可恢复，是否继续？',
      success: async (res) => {
        if (!res.confirm) return
        wx.showLoading({ title: '删除中...' })
        try {
          const result = await app.request({
            url: `/admin/users/delete/${id}`,
            method: 'DELETE'
          })
          wx.hideLoading()
          if (result.code === 200) {
            wx.showToast({ title: '已删除', icon: 'success' })
            this.loadUsers(true)
          } else {
            wx.showToast({ title: result.message || '删除失败', icon: 'none' })
          }
        } catch (error) {
          wx.hideLoading()
          wx.showToast({ title: '删除失败', icon: 'none' })
        }
      }
    })
  }
})

