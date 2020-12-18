// Color scales.
// The gradient functions change the "help" sidebar scales dynamically.
// The scale functions change recent period line width and color.

recentEBScale = 
    (max, total)=>{
        if(max > 10)
            return d3.scalePow()
                .domain([1,max/5,max])
                .range(["rgb(150,200,240)", "rgb(50,170,235)","rgb(90,255,0)"])
                .exponent(0.95)(total);
        else
            return d3.scalePow()
                .domain([1,2,10])
                .range(["rgb(150,200,240)","rgb(50,170,235)","rgb(90,255,0)"])
                .exponent(0.95)(total);
    }

recentEBGradient = 
    (max)=>{
        return (max > 10)
                ? "linear-gradient(90deg, rgba(190,210,230,0.7) 0%, rgba(170,210,240,0.7) "
                    + (2/max * 100) + "%, rgba(50,170,235,0.7) " + ((2+max/5) / max * 100) + "%, rgba(90,255,0,0.7) 100%)"
                : "linear-gradient(90deg, rgba(178,223,247,0.7) 0%, rgba(50,170,235,0.7) 20%, rgba(90,255,0,0.7) 100%)";
    }

recentEBWidthScale = 
    (max, total)=>{
        if(max > 10)
            return d3.scaleLog()
                .domain([1,2,max/2,max])
                .range([1.5,3,7,9])(total);
        else
            return d3.scaleLog()
                .domain([1,10])
                .range([2,9])(total);
    }

historyHMGradient = "linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(40,40,40, 0.6) 50%, rgba(130,110,160,0.5) 90%, rgba(40,1,65,0.4) 100%)"

historyGridGradient =
    (max)=>{
        if(max > 2000){
            return "linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(40,1,65,0.1) " + (10 / max * 100) + "%,\
                        rgba(40,1,65,0.2) " + (100 / max * 100) + "%, rgba(40,1,65,0.2) " + (500 / max * 100) + "%,\
                        rgba(40,1,65,0.25) " + (500 / max * 100) + "%, rgba(40,1,65,0.3) " + (1000 / max * 100) + "%,\
                        rgba(40,1,65,0.375) 50%, rgba(40,1,65,0.4) 100%)"
        }
        else if(max > 10){
            return "linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(40,1,65,0.2) 25%,\
                        rgba(40,1,65,0.3) 33.3%, rgba(40,1,65,0.375) 50%, rgba(40,1,65,0.4) 100%)"
        } else{ 
            return "linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(40,1,65,0.4) 100%)";
        }
    }