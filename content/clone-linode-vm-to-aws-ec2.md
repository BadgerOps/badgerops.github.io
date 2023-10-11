+++
title = "Export/Clone Linode VPS to AWS EC2"
date = "2020-03-03T12:28:44Z"
draft = false
+++

<p>Today we're looking at two methods of migrating a Linode Linux instance to an AWS EC2 instance. We can use <a href="https://www.linode.com/docs/platform/disk-images/copying-a-disk-image-over-ssh/">the official Linode disk copy guide</a> as a starting point, but that doesn't really get us all the way there, as we still need to <em>import</em> that image. This guide will walk you through the following:</p><h3 id="harder-but-more-flexible-process-if-you-can-t-create-a-second-disk-image-in-linode-based-on-instance-size-">Harder, but more flexible process if you can't create a second disk image in Linode (based on instance size)</h3><ul><li>Create disk image of your target Linode</li><li>Copy the disk image to S3 so we can use the AWS snapshot import tool</li><li>Import disk image to AWS as a disk snapshot</li><li>Create new EC2 instance</li><li>Write snapshot to EC2 volume</li><li>Update fstab, grub, network interface configuration on EC2 </li><li> <s>Profit</s> Reboot and use the new cloned image</li></ul><h3 id="easier-process-if-you-are-able-to-create-a-second-disk-in-your-linode-of-a-slightly-larger-size-than-your-main-disk">Easier process if you are able to create a second disk in your Linode of a slightly larger size than your main disk</h3><ul><li>Create disk image of your target Linode</li><li>Copy the disk image to S3 so we can use the AWS AMI import tool</li><li>Import disk image to AWS as an AMI</li><li>Create new EC2 from that AMI</li></ul><h5 id="please-read-through-both-sets-of-instructions-to-familiarize-yourself-with-the-process-then-follow-along-i-would-love-feedback-you-can-reach-me-badgerops-on-twitter-or-find-my-email-address-on-my-profile-and-reach-out-that-way-thank-you-">Please read through both sets of instructions to familiarize yourself with the process, then follow along! I would love feedback, you can reach me <code>@badgerops</code> on Twitter, or find my email address on my profile and reach out that way. Thank you!</h5><p>The first thing we'll do is ensure we have the needed pre-requisites, as well as <em>a written down process</em>, as there are a couple of ways to accomplish the import depending on the resources you have available.</p><p>1: You'll need AWS CLI credentials, or, the ability to create IAM roles &amp; policies from the AWS Console.</p><p>2: You'll need either enough disk space in your Linode to create an image of the disk, or a large enough EC2 Volume attached to an EC2 instance to copy the image to over SSH so you can then import the image.</p><p>3: A written procedure for what you're doing, don't just follow along with this post! Write down your steps and mark them off as you go so you don't do what I did and have to go back and do a step over again that you missed. Ask me how I came up with this pre-requisite.</p><h6 id="a-quick-note-on-linode-vps-disks-based-on-the-linode-size-you-have-chosen-and-the-way-you-configured-your-disks-initially-you-may-or-may-not-have-enough-disk-space-to-create-your-disk-image-in-linode-you-have-a-couple-options-">A quick note on Linode VPS disks: based on the Linode size you have chosen, and the way you configured your disks initially, you may or may not have enough disk space to create your disk image in Linode. You have a couple options:</h6><ul><li>Resize your Linode to be a bigger instance, choose the instance that will (at least) double your current storage size, so you can create an image</li><li>Copy the disk image over SSH as its being created to another EC2 instance (or your workstation) so you can import it from there. Your target EC2 or workstation will need to have enough disk space for the image you're creating.</li></ul><h4 id="now-on-to-the-guide-">Now, on to the guide:</h4><hr><h4 id="note-if-you-d-like-to-follow-along-with-the-aws-guide-for-importing-a-vm-image-snapshot-the-documentation-is-available-here">NOTE: If you'd like to follow along with the AWS guide for importing a VM/Image/Snapshot, the documentation is available <a href="https://docs.aws.amazon.com/vm-import/latest/userguide/vmimport-image-import.html">here</a></h4><p></p><h3 id="create-s3-bucket">Create S3 bucket</h3><p>From the AWS Console, navigate to S3 and create a bucket, or identify an existing S3 bucket you'd like to use to store the disk image. You could also use the AWS CLI tool to create your S3 bucket. Due to the way the AWS vm import tool works, we have to use an S3 bucket.</p><h3 id="create-iam-role-and-policy">Create IAM Role and Policy</h3><p></p><p>First we'll look at the role and policy you need to create regardless of whether you're using AWS CLI credentials, or if you only have access to the AWS Console. This policy allow you to read from the S3 bucket, and write to EC2 to create a snapshot.</p><ol><li>A role to allow you to import a VM (or, in our case a disk image)</li><li>A policy to allow your credentials, or EC2 instance to run the import. This will be assigned to the role.</li></ol><p>Here is the example role in json format:</p><!--kg-card-begin: markdown--><pre><code class="language-import-role.json">{
   &quot;Version&quot;: &quot;2012-10-17&quot;,
   &quot;Statement&quot;: [
      {
         &quot;Effect&quot;: &quot;Allow&quot;,
         &quot;Principal&quot;: { &quot;Service&quot;: &quot;vmie.amazonaws.com&quot; },
         &quot;Action&quot;: &quot;sts:AssumeRole&quot;,
         &quot;Condition&quot;: {
            &quot;StringEquals&quot;:{
               &quot;sts:Externalid&quot;: &quot;import-vm-role&quot;
            }
         }
      }
   ]
}</code></pre>
<!--kg-card-end: markdown--><p>Save this as <code>vm-import-role.json</code></p><p>You can <a href="https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-user.html">create a new role in the AWS Console</a>, or run the following command from the AWS CLI:</p><!--kg-card-begin: markdown--><pre><code>aws iam create-role --role-name import-vm-role --assume-role-policy-document &quot;file:///path/to/import-vm-role.json&quot;
</code></pre>
<!--kg-card-end: markdown--><p>Next, we'll create the policy that allows us to read from the S3 bucket that we'll put the image in, and upload the image to EC2 as a snapshot:</p><h4 id="note-you-ll-need-to-insert-your-s3-bucket-name-where-i-have-s3_bucket_name-listed-in-the-resource-section">Note: you'll need to insert your S3 bucket name where I have &lt;s3_bucket_name&gt; listed in the resource section</h4><!--kg-card-begin: markdown--><pre><code>{
   &quot;Version&quot;:&quot;2012-10-17&quot;,
   &quot;Statement&quot;:[
      {
         &quot;Effect&quot;:&quot;Allow&quot;,
         &quot;Action&quot;:[
            &quot;s3:GetBucketLocation&quot;,
            &quot;s3:GetObject&quot;,
            &quot;s3:ListBucket&quot;
         ],
         &quot;Resource&quot;:[
            &quot;arn:aws:s3:::&lt;s3_bucket_name&gt;&quot;,
            &quot;arn:aws:s3:::&lt;s3_bucket_name&gt;/*&quot;
         ]
      },
      {
         &quot;Effect&quot;:&quot;Allow&quot;,
         &quot;Action&quot;:[
            &quot;s3:GetBucketLocation&quot;,
            &quot;s3:GetObject&quot;,
            &quot;s3:ListBucket&quot;,
            &quot;s3:PutObject&quot;,
            &quot;s3:GetBucketAcl&quot;
         ],
         &quot;Resource&quot;:[
            &quot;arn:aws:s3:::&lt;s3_bucket_name&gt;&quot;,
            &quot;arn:aws:s3:::&lt;s3_bucket_name&gt;/*&quot;
         ]
      },
      {
         &quot;Effect&quot;:&quot;Allow&quot;,
         &quot;Action&quot;:[
            &quot;ec2:ModifySnapshotAttribute&quot;,
            &quot;ec2:CopySnapshot&quot;,
            &quot;ec2:RegisterImage&quot;,
            &quot;ec2:Describe*&quot;
         ],
         &quot;Resource&quot;:&quot;*&quot;
      }
   ]
}

</code></pre>
<!--kg-card-end: markdown--><p>Save this as <code>vm-import-policy.json</code></p><p>Once again, you can <a href="https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_create-console.html#access_policies_create-json-editor">use the AWS Console</a> to create the policy, or run the following command from the AWS CLI:</p><pre><code>aws iam put-role-policy --role-name import-vm-role --policy-name import-vm-policy --policy-document "file:///path/to/vm-import-policy.json"</code></pre><h3 id="prepare-linode-for-backup">Prepare Linode for backup</h3><p>At this point you'll want to have your plan in place for how you're planning on backing up your Linode, as we're going to shut the Linode down for the next few steps. </p><ul><li>Ensure everyone using your Linode knows you're shutting it down!</li><li>NOTE: if you have sensitive data and/or a database on this Linode, consider taking a backup before proceeding.</li><li>Reboot Linode to the Finnix <a href="https://www.linode.com/docs/troubleshooting/rescue-and-rebuild/">recovery environment</a> </li><li>Connect to your Linode using <a href="https://www.linode.com/docs/platform/manager/remote-access/#console-access">Lish</a></li></ul><p>If you've decided to back up to a second disk on your Linode and import from there, skip the next section and go to the "Create disk image to Linode second disk (simple/fast method)" section. If you're copying your image over SSH to an existing EC2 instance, or your workstation (this is what I did) then keep reading.</p><h3 id="create-disk-image-from-linode-over-ssh-tunnel">Create disk image from Linode over SSH tunnel</h3><p>First create a (long!) root password and start the SSH service so we can connect to this Linode to create the image. You could also use ssh keys if you'd prefer not to use password based authentication.</p><figure class="kg-card kg-code-card"><pre><code>passwd
service ssh start</code></pre><figcaption>Set a root password and start ssh</figcaption></figure><p>Next, from your <em>existing</em> EC2 instance, or workstation run the following command from a screen (or Tmux) session. (In case you lose connection to your EC2 instance, you don't want the backup command to fail)</p><pre><code>ssh root@&lt;linode_ip&gt; "dd if=/dev/sda " | dd of=/path/to/linode.img</code></pre><p>This command will use the Linux <a href="https://www.gnu.org/software/coreutils/manual/html_node/dd-invocation.html#dd-invocation">dd</a> utility to copy from your Linode to an image on your EC2 or workstation. </p><p>Depending on how large your Linode is, and how much bandwidth you have available to you, this could take a few hours. Once the command completes, move on to preparing and importing the image to S3.</p><h3 id="prepare-disk-image-for-import-to-aws-s3">Prepare disk image for import to AWS S3</h3><p><em>optional</em> do the following steps to shrink the disk image if you have a large amount of free space! In this example, I had a vastly overprovisioned Linode and wanted to reduce the size of the image before import.</p><pre><code class="language-bash"># first, verify the overall size of the image
du -h -s linode.img

1.3T linode.img

# create loop partition

losetup --find --partscan linode.img

# verify it got created and has the size we expect

lsblk | grep loop0
NAME          MAJ:MIN RM  SIZE RO TYPE MOUNTPOINT
loop0           7:0    0  1.3T  0 loop

fdisk -l /dev/loop0
Disk /dev/loop0: 1.3 TiB, 1373856858112 bytes, 2683314176 sectors
Units: sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 512 bytes
I/O size (minimum/optimal): 512 bytes / 512 bytes

# for paranoia's sake, run e2fsck

e2fsck -f /dev/loop0 

# mount the image for the next few steps

mkdir -p /mnt/linodeimg

mount /dev/loop0 /mnt/linodeimg

# then run fstrim on it, we can use fstrim to remove any blocks not used # by the filesystem as noted in the man page:
# "fstrim is used on a mounted filesystem to discard (or "trim") blocks # which are not in use by the filesystem.  This is useful for 
# solid-state drives (SSDs) and thinly-provisioned storage.

fstrim -v /mnt/linodeimg
/mnt/linodeimg: 1 TiB (1138564808704 bytes) trimmed (wow!)

# unmount the loop partition

umount /dev/loop0

# confirm the physical disk is resized

du -h -s linode.img
220G    linode.img

# now that the actual size is reduced, we'll also want to reduce 
# the fileystem size because it still thinks its 1.3T in size!

lsblk
NAME          MAJ:MIN RM  SIZE RO TYPE MOUNTPOINT
loop0           7:0    0  1.3T  0 loop

resize2fs linode.img 250G

lsblk
NAME          MAJ:MIN RM  SIZE RO TYPE MOUNTPOINT
loop0           7:0    0  250G  0 loop

# remove the loop device map

losetup -d /dev/loop0</code></pre><p>Now we copy the image into the S3 bucket that we've prepared previously:</p><pre><code>aws s3 cp linode.img s3://&lt;your_s3_bucket_name&gt;/&lt;image_path&gt;
Completed 56.0 GiB/250.0 GiB (138.1 MiB/s) with 1 file(s) remaining</code></pre><p>Following along with <a href="https://docs.aws.amazon.com/vm-import/latest/userguide/vmie_prereqs.html">https://docs.aws.amazon.com/vm-import/latest/userguide/vmie_prereqs.html</a> we'll import the image using the policy and role we created previously.</p><p>Create a <code>containers.json</code> file with the following format:</p><pre><code class="language-json">[
  {
    "Description": "Linode Image",
    "Format": "raw",
    "UserBucket": {
        "S3Bucket": "&lt;your_s3_bucket_name&gt;",
        "S3Key": "&lt;image_path&gt;/linode.img"
    }
}]</code></pre><p>Now, import the disk as a snapshot:</p><pre><code>time aws ec2 import-snapshot --region us-west-2 --description "Imported Linode Image" --disk-container "file:///containers.json"
{
    "SnapshotTaskDetail": {
        "Status": "active",
        "Description": "Linode Image",
        "Format": "RAW",
        "DiskImageSize": 0.0,
        "UserBucket": {
            "S3Bucket": "&lt;s3_bucket_name&gt;",
            "S3Key": "linode.img"
        },
        "Progress": "3",
        "StatusMessage": "pending"
    },
    "Description": "Linode Image",
    "ImportTaskId": "import-snap-&lt;uuid&gt;"
}</code></pre><p>Note: we can monitor the progress by running:</p><pre><code>aws ec2 describe-import-snapshot-tasks --import-task-ids import-snap-&lt;uuid_from_above&gt; --region us-west-2
{
    "ImportSnapshotTasks": [
        {
            "SnapshotTaskDetail": {
                "Status": "active",
                "Description": "Linode Image",
                "Format": "RAW",
                "DiskImageSize": 268435456000.0,
                "UserBucket": {
                    "S3Bucket": "&lt;s3_bucket_name&gt;",
                    "S3Key": "linode.img"
                },
                "Progress": "35",
                "StatusMessage": "downloading/converting"
            },
            "Description": "Linode Image",
            "ImportTaskId": "import-snap-&lt;uuid&gt;"
        }
    ]
}</code></pre><p>Once that import has completed, create a new EC2 image and <strong>let it boot</strong> - we need to grab a few files off of it!</p><p>While its booting, create a new volume of the desired size from the snapshot we just imported. Attach it to the instance and log into the instance once it has booted.</p><p>Mount the new volume to <code>/mnt</code> as shown here:</p><pre><code># NOTE: your exact path might differ, use lsblk command to see what the 
# correct path is

mount /dev/nvme2n1p1 /mnt 
</code></pre><p>We'll need to re-install grub on the new disk image, specify root-directory as <code>/mnt</code> since thats where we mounted the image:</p><pre><code>grub-install --recheck --debug --root-directory=/mnt /dev/nvme2n1
</code></pre><p>Next prepare to <code>chroot</code> into the image by mounting the required filesystems:</p><pre><code>for i in /dev /dev/pts /proc /sys /run; do sudo mount -B $i /mnt$i; done</code></pre><p>We’ll also grab the netplan config from the  ec2 instance to apply to the new image:</p><pre><code>cp /etc/network/interfaces.d/50-cloud-init.cfg /mnt/etc/network/interfaces.d/50-cloud-init.cfg</code></pre><h4 id="important-run-a-blkid-to-get-the-uuid-of-your-new-image-and-save-that-uuid-for-below">IMPORTANT: run a <code>blkid</code> to get the UUID of your new image and save that UUID for below</h4><p>Since we imported the image and created a new volume, the UUID will have changed, we need to update <code>/etc/fstab</code> or else we won't be able to boot!</p><p>Then we'll finally <code>chroot</code> in for the last few changes</p><pre><code>chroot /mnt

# change the hostname to your desired hostname

echo 'yourhostname' &gt; /etc/hostname

# don't forget to update /etc/hosts with your desired hostname

vi /etc/hosts

# edit /etc/fstab with the new UUID for your image you got from 
# the blkid command above

vi /etc/fstab

# then update grub

update-grub

# thats it! If you have anything else you want to update, do that now.

exit</code></pre><p>Unmount the filesystems:</p><pre><code>for i in /dev /dev/pts /proc /sys /run; do umount /mnt$i ; done

unmount /mnt</code></pre><p>Finally shut down the EC2 instance, and disconnect the volumes from it, then remount the new volume you just created from the snapshot as <code>/dev/sda1</code> and reboot the EC2. You should now be able to log in to your clone of your Linode!</p><p>This process was long and painful to figure out, but I wanted to capture this process to demonstrate that you can still do it if you don't have the ability to create a 'local to Linode' disk image. For the easier path, follow along with the next section.</p><h3 id="create-disk-image-to-linode-second-disk-simple-fast-method-">Create disk image to Linode second disk (simple/fast method)</h3><h6 id="note-if-you-use-this-method-you-must-have-aws-cli-access-as-this-method-must-use-the-aws-cli-tools-to-import-the-disk-image-">NOTE: if you use this method, you MUST have AWS CLI access as this method must use the AWS CLI tools to import the disk image.</h6><p>This is a much simpler/faster method, which is the recommended path if you are able to create a local image in your Linode instance, based on your disk space available. Its adapted from Devon Kurland's post <a href="https://devonkurland.com/importing-a-linode-vps-into-aws-ec2/">here</a>.</p><p>If you've chosen to create your disk image on a second disk in your Linode, you'll want to do the following steps:</p><ul><li>Shut down your Linode</li><li>Add a second disk that is larger than your primary disk (so you'll have enough room for the disk image to be created)</li><li>Set the new disk to be <code>/dev/sdb</code> in the Linode console</li><li>Boot into Finnix recovery mode</li></ul><p>Now, connect via <a href="https://www.linode.com/docs/platform/manager/remote-access/#console-access">Lish</a> for the rest of the commands.</p><pre><code># First, install required tools to the Finnix recovery environment

apt-get update
apt-get install python-pip python-setuptools ca-certificates grub2
# When prompted where to install GRUB2, just press Enter, and then select Yes to continue without installing.

# Install the AWS CLI which we'll use to import the image
pip install awscli

# Next, mount the new disk that we'll be creating the backup on and create the server.raw file

mount /dev/sdb /mnt ; cd /mnt
dd if=/dev/zero of=server.raw count=1 bs=1MiB

# Next, copy your Linode primary disk to the raw file
dd bs=1MiB seek=1 if=/dev/sda of=server.raw

# Next, some quick fdisk prep, create a partition and write it
fdisk server.raw
# Press n, accept all of the defaults, then a and w.

# Next, use https://linux.die.net/man/8/kpartx to create a device map from the image so we can then mount it

kpartx -a -v server.raw

mount /dev/mapper/loop1p1 /mnt
# If you receive a "does not exist" error, you may need to run the last two commands again.

# next we'll (re) install grub to the image we just mounted as a loop device. This ensures the MBR has grub installed

grub-install --recheck --debug --boot-directory=/mnt/boot/ /dev/loop1

# Prepare to chroot into the new image
mount -t proc proc /mnt/proc/ ; mount -t sysfs sys /mnt/sys/
mount -o bind /dev /mnt/dev/
chroot /mnt

# Configure the new image, verify grub is installed and re-update it
apt-get install grub2-common linux-image-amd64
cp /usr/share/grub/default/grub /etc/default/grub
update-grub2

# Update our fstab with the new disk UUID
sed -i "s/insmod ext2/insmod ext2\nset root='hd0,msdos1'/g"
echo "UUID=`blkid -s UUID -o value /dev/sda` / ext4 defaults 1 1" &gt; /etc/fstab
printf "nameserver 8.8.8.8\nnameserver 8.8.4.4" &gt; /etc/resolv.conf
printf "auto lo\niface lo inet loopback\n\nauto eth0\niface eth0 inet dhcp" &gt; /etc/network/interfaces

# Do any other steps you might want to do, then exit
exit

# Unmount all the filesystems
for i in proc sys dev ; do umount /mnt/$i ; done
umount /mnt

# Remove the device maps

kpartx -d -v server.raw</code></pre><p>Once you're done here, the next 2 commands will import your image to S3, then to EC2 as an image.</p><pre><code>aws s3 cp server.raw s3://&lt;your_s3_bucket_name&gt;/&lt;image_path&gt;</code></pre><pre><code>aws ec2 import-image --cli-input-json "{\"Description\":\"server\",\"DiskContainers\":[{\"Description\":\"Imported from Linode\",\"UserBucket\":{\"S3Bucket\":\"bucketname\",\"S3Key\":\"server.raw\"}}]}"</code></pre><p>To monitor the import task you can run the following command:</p><pre><code>aws ec2 describe-import-image-tasks</code></pre><p>Once your import is complete you can navigate to "My AMI's" and create an EC2 instance from there. </p>