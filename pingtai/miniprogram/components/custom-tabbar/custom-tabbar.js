// components/custom-tabbar/custom-tabbar.js
Component({
  properties: {
    active: {
      type: Number,
      value: 0
    },
    tabs: {
      type: Array,
      value: []
    }
  },

  methods: {
    switchTab(e) {
      const { index, path } = e.currentTarget.dataset
      if (index !== this.data.active) {
        this.triggerEvent('change', { index, path })
        wx.switchTab({ url: '/' + path })
      }
    }
  }
})
