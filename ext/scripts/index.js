(function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
(i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
})(window,document,'script','https://www.google-analytics.com/analytics.js','ga');

ga('create', 'UA-186188545-1', 'auto');

// Modifications:
ga('set', 'checkProtocolTask', null); // Disables file protocol checking.
ga('send', 'pageview', '/popup'); // Set page, avoiding rejection due to chrome-extension protocol

window.onload = function() {
    let app = new Vue({
        el: '#app',
        data: {
            articles: [],
            largeMode: true,
            readingList: [],
            page: "main"
        },
        async mounted() {
            let res = await fetch(`https://bestofhn.storage.googleapis.com/news/bing_ScienceAndTechnology.json`)
            let data = await res.json()
            this.articles = data.value
            if (localStorage.getItem("largeMode")) {
                this.largeMode = JSON.parse(localStorage.getItem("largeMode"))
            }
            if (localStorage.getItem("readingList")) {
                this.readingList = JSON.parse(localStorage.getItem("readingList"))
            }
        },
        methods: {
            timeSince: function(date) {

                var seconds = Math.floor((new Date() - new Date(date)) / 1000);

                var interval = seconds / 31536000;

                if (interval > 1) {
                    return Math.floor(interval) + " years";
                }
                interval = seconds / 2592000;
                if (interval > 1) {
                    return Math.floor(interval) + " months";
                }
                interval = seconds / 86400;
                if (interval > 1) {
                    return Math.floor(interval) + " days";
                }
                interval = seconds / 3600;
                if (interval > 1) {
                    return Math.floor(interval) + " hours";
                }
                interval = seconds / 60;
                if (interval > 1) {
                    return Math.floor(interval) + " minutes";
                }
                return Math.floor(seconds) + " seconds";
            },
            addToReadingList: function(article) {
                this.articles.splice(this.articles.indexOf(article), 1)
                for (let readingListItem of this.readingList) {
                    if (readingListItem.url === article.url) {
                        return
                    }
                }
                this.readingList.push(article)
            },
            removeFromReadingList: function(article) {
                for (let i = 0; i < this.readingList.length; i++) {
                    if (this.readingList[i].url === article.url) {
                        this.readingList.splice(i, 1)
                    }
                }
                return true
            },
        },
        watch: {
            largeMode: function(newVal, oldVal) {
                localStorage.setItem("largeMode", JSON.stringify(newVal))
            },
            readingList: function(newVal, oldVal) {
                localStorage.setItem("readingList", JSON.stringify(newVal))
            }

        }
    })
}