import subprocess

out = subprocess.Popen(['cdk', 'synth', 'cdk-blog-vpc1'], cwd="cdk-blog-vpc",
           stdout=subprocess.PIPE, 
           stderr=subprocess.STDOUT)
out.wait()
stdout,stderr = out.communicate()
print(stdout)