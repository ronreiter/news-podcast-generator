window.onload = function() {
    let app = new Vue({
        el: '#app',
        data: {
            articles: []
        },
        async mounted() {
            let res = await fetch(`https://bestofhn.storage.googleapis.com/news/bing_ScienceAndTechnology.json`)
            let data = await res.json()
            this.articles = data.value
        },
        methods: {
            timeSince: (date) => {

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
            }
        }
    })
}