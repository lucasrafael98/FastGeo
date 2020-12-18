// sidebar code
$(document).ready(()=>{
    $(".sidebar-btn").on("click",(e)=>{
        if($(e.currentTarget.hash).css("display") == "none"){
            $(".sidebar-pane").css("display","none");
            $("#sidebar-content").css("width","11.9vw");
            $(e.currentTarget.hash).css("display","block");
        } else {
            $("#sidebar-content").css("width","0vw");
            $(e.currentTarget.hash).css("display","none");
        }
    });
});