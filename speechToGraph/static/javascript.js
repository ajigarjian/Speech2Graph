document.addEventListener('DOMContentLoaded', function() {

    document.getElementById("userInputForm").addEventListener("submit", function(event){
          event.preventDefault();
          handleFiles();
    })
    
    function handleFiles() {

        const file = document.getElementById("audio_input").files[0];
        const reader = new FileReader();

        //Set up a listener so that once we call reader.readAsDataURL, it captures the output in a variable
        reader.onload = (e) => {
            const audio_data = e.target.result;

            fetch('/transcribe', {
                method: 'POST',
                body: JSON.stringify({
                    file : audio_data
              })
            })
    
            // Receive response from server side to know if post was successfully added to database or not
            .then(response => response.json())
            .then(result => {   
                document.getElementById("transcription").innerHTML=result["transcribed_text"];
                document.getElementById("label").innerHTML=result["text_label"];
                document.getElementById("score").innerHTML=result["text_score"];
            });
        };

        //Now read the file
        reader.readAsDataURL(file);
        
    }

})