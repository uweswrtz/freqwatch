source "docker" "python" {
  image  = "python"
  commit = true
  changes = [
      "WORKDIR /usr/src/app",
      "CMD [\"python\", \"freqwatch.py\"]",
      "ENTRYPOINT [\"\"]"
      
    ]
}
// "ENTRYPOINT [\"/bin/sh\", \"-c\"]"
// "CMD [\"python\", \"botwatcher.py\"]"


// "pip install pip --upgrade",      
build {
  name = "freqwatch"
  sources = [
    "source.docker.python"
  ]
  
  provisioner "file" {
    source = "./"
    destination = "/usr/src/app"
  }
  
  provisioner "shell" {
    environment_vars = [
      "FOO=hello world",
    ]
    inline = [
      
      "python -m pip install -r requirements.txt",

    ]
  }
  
  post-processor "docker-tag" {
    repository = "freqwatch"
    tags = ["1"]
  }
}