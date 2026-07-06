// pages/admin/export/export.js
const app = getApp()

Page({
  data: {
    selectedType: 'bookings',
    period: 'month',
    exporting: false,
    previewData: [],
    previewHeaders: []
  },

  onLoad: function() {
    if (!app.checkLogin()) return
    this.loadPreviewData()
  },

  // 下拉刷新
  onPullDownRefresh: function() {
    this.loadPreviewData()
    setTimeout(() => {
      wx.stopPullDownRefresh()
    }, 1000)
  },

  // 选择报表类型
  selectReport: function(e) {
    const type = e.currentTarget.dataset.type
    this.setData({ selectedType: type })
    this.loadPreviewData()
  },

  // 设置时间范围
  setPeriod: function(e) {
    const period = e.currentTarget.dataset.period
    this.setData({ period })
    this.loadPreviewData()
  },

  // 加载预览数据
  loadPreviewData: function() {
    const token = wx.getStorageSync('token')
    const period = this.data.period
    const selectedType = this.data.selectedType
    
    // 映射报表类型到API路径
    const pathMap = {
      'bookings': '/admin/stats/bookings',
      'users': '/admin/stats/users',
      'facilities': '/admin/stats/facilities',
      'feedbacks': '/admin/stats/feedbacks',
      'auditors': '/admin/stats/auditors'
    }
    
    wx.request({
      url: `${app.globalData.baseUrl}${pathMap[selectedType] || '/admin/stats/bookings'}?period=${period}`,
      header: { 'Authorization': `Bearer ${token}` },
      success: (res) => {
        if (res.data.code === 200) {
          this.setData(this.formatPreviewData(res.data.data))
        }
      }
    })
  },

  // 格式化预览数据
  formatPreviewData: function(data) {
    let previewData = []
    let previewHeaders = []
    
    if (this.data.selectedType === 'bookings') {
      previewHeaders = ['日期', '总数', '待审核', '已通过', '已拒绝', '已完成']
      if (data.daily && data.daily.length > 0) {
        previewData = data.daily.map(item => ({
          日期: item.date,
          总数: item.count,
          待审核: data.status_distribution?.pending || 0,
          已通过: data.status_distribution?.approved || 0,
          已拒绝: data.status_distribution?.rejected || 0,
          已完成: data.status_distribution?.completed || 0
        }))
      }
    } else if (this.data.selectedType === 'users') {
      previewHeaders = ['用户名', '手机号', '预约数']
      previewData = (data.active_users || []).map(item => ({
        用户名: item.username,
        手机号: item.phone,
        预约数: item.booking_count
      }))
    } else if (this.data.selectedType === 'facilities') {
      previewHeaders = ['设施名', '类别', '预约数', '签到数', '使用率']
      previewData = (data.rankings || []).map(item => ({
        设施名: item.name,
        类别: item.category,
        预约数: item.booking_count,
        签到数: item.checkin_count,
        使用率: item.usage_rate + '%'
      }))
    } else if (this.data.selectedType === 'feedbacks') {
      previewHeaders = ['总反馈数', '待处理', '已处理']
      previewData = [{
        总反馈数: data.total || 0,
        待处理: data.status_distribution?.pending || 0,
        已处理: (data.status_distribution?.resolved || 0) + (data.status_distribution?.replied || 0)
      }]
    } else if (this.data.selectedType === 'auditors') {
      previewHeaders = ['审核员', '手机号', '审核数', '通过数', '拒绝数', '通过率']
      previewData = (data.auditors || []).map(item => ({
        审核员: item.username,
        手机号: item.phone,
        审核数: item.total_audited,
        通过数: item.approved,
        拒绝数: item.rejected,
        通过率: item.approval_rate + '%'
      }))
    }
    
    return { previewData, previewHeaders }
  },

  // 导出报表
  handleExport: function() {
    const app = getApp()
    const token = wx.getStorageSync('token')
    
    if (this.data.previewData.length === 0) {
      wx.showToast({ title: '暂无数据可导出', icon: 'none' })
      return
    }

    this.setData({ exporting: true })

    // 显示加载提示
    wx.showLoading({ title: '正在生成报表...' })

    // 调用后端导出接口
    const reportTypes = {
      'bookings': '预约报表',
      'users': '用户报表',
      'facilities': '设施报表',
      'feedbacks': '反馈报表',
      'auditors': '审核员报表'
    }

    wx.request({
      url: `${app.globalData.baseUrl}/admin/export/excel?type=${this.data.selectedType}&period=${this.data.period}`,
      header: { 
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      responseType: 'arraybuffer',
      success: (res) => {
        wx.hideLoading()
        
        if (res.statusCode === 200) {
          // 将ArrayBuffer转换为Base64
          const base64 = wx.arrayBufferToBase64(res.data)
          const fileName = `${reportTypes[this.data.selectedType]}_${this.getPeriodName()}.xlsx`
          
          // 保存到本地文件
          const fs = wx.getFileSystemManager()
          const savedFilePath = `${wx.env.USER_DATA_PATH}/${fileName}`
          
          fs.writeFile({
            filePath: savedFilePath,
            data: base64,
            encoding: 'base64',
            success: () => {
              // 打开文件
              wx.openDocument({
                filePath: savedFilePath,
                fileType: 'xlsx',
                showMenu: true,
                success: () => {
                  wx.showModal({
                    title: '导出成功',
                    content: 'Excel文件已生成并打开，您可以在右上角菜单中分享或保存文件。',
                    showCancel: true,
                    confirmText: '分享',
                    cancelText: '完成',
                    success: (modalRes) => {
                      if (modalRes.confirm) {
                        // 分享文件
                        wx.shareFileMessage({
                          filePath: savedFilePath,
                          fileName: fileName,
                          success: () => {
                            console.log('分享成功')
                          },
                          fail: (err) => {
                            console.error('分享失败', err)
                          }
                        })
                      }
                    }
                  })
                },
                fail: (err) => {
                  console.error('打开文件失败', err)
                  wx.showToast({ title: '文件生成失败', icon: 'none' })
                }
              })
            },
            fail: (err) => {
              console.error('保存文件失败', err)
              wx.showToast({ title: '文件保存失败', icon: 'none' })
            }
          })
        } else {
          wx.showToast({ title: '导出失败', icon: 'none' })
        }
      },
      fail: (err) => {
        wx.hideLoading()
        console.error('导出请求失败', err)
        wx.showToast({ title: '网络请求失败', icon: 'none' })
      },
      complete: () => {
        this.setData({ exporting: false })
      }
    })
  },

  getReportTypeName: function() {
    const names = {
      bookings: '预约报表',
      users: '用户报表',
      facilities: '设施报表',
      feedbacks: '反馈报表',
      auditors: '审核员报表'
    }
    return names[this.data.selectedType] || '未知报表'
  },

  getPeriodName: function() {
    const names = {
      today: '今日',
      week: '本周',
      month: '本月',
      year: '本年',
      all: '全部'
    }
    return names[this.data.period] || '未知'
  }
})
