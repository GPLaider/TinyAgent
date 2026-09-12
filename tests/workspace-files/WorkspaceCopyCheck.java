package io.github.gplaider.tinyagent;

import java.io.*;
import java.util.Arrays;

public class WorkspaceCopyCheck {
    interface Checked { void run() throws Exception; }
    static int checks;
    static void require(boolean value,String label){if(!value)throw new AssertionError(label);checks++;}
    static IOException failure(Checked task)throws Exception {
        try{task.run();throw new AssertionError("Expected failure");}
        catch(IOException expected){checks++;return expected;}
    }
    public static void main(String[] args)throws Exception {
        byte[] bytes=new byte[150003];for(int i=0;i<bytes.length;i++)bytes[i]=(byte)i;
        ByteArrayOutputStream output=new ByteArrayOutputStream();
        require(WorkspaceCopy.copy(new ByteArrayInputStream(bytes),output,bytes.length)==bytes.length,"copy byte count");
        require(Arrays.equals(bytes,output.toByteArray()),"copy bytes across buffer boundary");
        output.reset();require(WorkspaceCopy.copy(new ByteArrayInputStream(new byte[0]),output,0)==0,"empty file");
        require(failure(()->WorkspaceCopy.copy(new ByteArrayInputStream(bytes),output,-1)).getMessage().contains("크기"),"unknown size");
        require(output.size()==0,"unknown size wrote bytes");
        require(failure(()->WorkspaceCopy.copy(new ByteArrayInputStream(new byte[1]),new ByteArrayOutputStream(),2)).getMessage().contains("작아졌"),"truncated source");
        ByteArrayOutputStream growingOutput=new ByteArrayOutputStream();
        InputStream endless=new InputStream(){
            @Override public int read(){return 'x';}
            @Override public int read(byte[] buffer,int offset,int length){Arrays.fill(buffer,offset,offset+length,(byte)'x');return length;}
        };
        require(failure(()->WorkspaceCopy.copy(endless,growingOutput,70000)).getMessage().contains("커졌"),"growing source rejected");
        require(growingOutput.size()==70000,"copy followed unbounded growth");
        InputStream stalled=new InputStream(){public int read(){return 0;}public int read(byte[] b,int o,int n){return 0;}};
        require(failure(()->WorkspaceCopy.copy(stalled,new ByteArrayOutputStream(),1)).getMessage().contains("진행"),"zero-progress source");
        IOException readError=new IOException("read failed"),writeError=new IOException("disk full");
        require(failure(()->WorkspaceCopy.copy(new InputStream(){public int read()throws IOException{throw readError;}},new ByteArrayOutputStream(),1))==readError,"original read error preserved");
        require(failure(()->WorkspaceCopy.copy(new ByteArrayInputStream(bytes),new OutputStream(){public void write(int b)throws IOException{throw writeError;}},bytes.length))==writeError,"original write error preserved");
        Thread.currentThread().interrupt();
        try {
            require(failure(()->WorkspaceCopy.copy(new ByteArrayInputStream(bytes),new ByteArrayOutputStream(),bytes.length)) instanceof InterruptedIOException,"interruption detected");
            require(Thread.currentThread().isInterrupted(),"interrupt flag preserved");
        } finally {Thread.interrupted();}
        ByteArrayOutputStream interruptedOutput=new ByteArrayOutputStream(){
            @Override public void write(byte[] bytes,int start,int count){super.write(bytes,start,count);Thread.currentThread().interrupt();}
        };
        try {
            require(failure(()->WorkspaceCopy.copy(new ByteArrayInputStream(bytes),interruptedOutput,bytes.length)) instanceof InterruptedIOException,"mid-copy interrupt detected");
            require(interruptedOutput.size()==65536,"continued copying after interrupt");
        } finally {Thread.interrupted();}
        System.out.println("PASS: "+checks+" bounded-copy checks (growth/truncation/I/O/interrupt/binary/empty)");
    }
}
