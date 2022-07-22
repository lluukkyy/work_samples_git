#include "stdio.h"
#include "stdlib.h"
#include "math.h"

#define MAX_BYTES 2048
#define MAX_NQUEUES 64
#define CELL_START 128
#define CELL_SIZE 30
#define CELL_STORAGE 27

#define Q unsigned char

unsigned char data[MAX_BYTES];

//Exit when reaching out of the memory.
void on_out_of_memory(){
    printf("Error: Out of memory.\n");
    exit(0);
}

//Exit on invalid operations.
void on_illegal_operation(){
    printf("Error: Invalid operation.\n");
    exit(0);
}

//Check the validity of a queue.
void QChecker(Q* q){
    //Check if q is valid. Exit otherwise.
    if (q == NULL || q>data+CELL_START-1 || q < data) on_illegal_operation();

    //Make sure this queue is initialized. Exit otherwise.
    if (*q == 0) on_illegal_operation();
}

//Find an available cell and activate it by marking 1 on 
//  the cell's local head ptr.
//Returns a unsigned int handle (cell ID: 1~64 inclusively) of the cell.
//If not found, return MAX_NQUEUES+1 (64+1 in this case).
unsigned int startANewCell(){
    for(unsigned int i=CELL_START; i<MAX_BYTES; i+=30){
        if(data[i] == 0) {
            //activate the cell by mark 1 on the local head ptr
            data[i] = 1;
            return (i-CELL_START)/30+1;
        }
    }
    return MAX_NQUEUES+1;
}

//Create a new queue.
//Returns a handle to the queue. 
//Exit the program when reaches limit number of queues or all cells are filled.
//Note that the handle is also stored at 'data'.
Q* create_queue(){
    //Find a valid handle for a new queue. Exit otherwise.
    Q* head = NULL;
    for(unsigned int i=0; i<CELL_START; i+=2){
        if(data[i] == 0) {
            head = data+i;
            break;
        }
    }
    if(head == NULL) on_out_of_memory();

    //Find a valid cell for storage and initilize it. Exit otherwise.
    unsigned int cellID = startANewCell();
    if (cellID == MAX_NQUEUES+1) on_out_of_memory();

    //Initialize head and tail by assigning an empty cell to them.
    *head = cellID;
    *(head+1) = cellID;

    return head;
}

//Put a new char element at the end of the queue.
//  *q -- the queue you would like to append
//  b -- the emelemt you would like to put
//Exit the program when hitting storage limit.
void enqueue_byte(Q* q, unsigned char b){
    //Check if q is valid. Exit if not.
    QChecker(q);

    unsigned int tailCell = (*(q+1) - 1) * CELL_SIZE + CELL_START;

    //Make sure the tail cell is activated. Exit otherwise.
    if(data[tailCell] == 0) on_illegal_operation();

    //If the tail cell is just activated, which means nothing has been stored yet.
    if(data[tailCell] == 1){
        //Assign local head and tail ptr to 3 representing t
        //  the local index of the first storage byte of the cell.
        data[tailCell] = 3;
        data[tailCell+1] = 3;

        //Put the value there.
        data[tailCell+3] = b;

        //Break out the funciton.
        return;
    }

    //Get the length of the circular queue inside the cell.
    //Note that(a mod b) in C is ( (a%b + b) % b ).
    //It's just simply (tail - head) mod CELL_STORAGE + 1. 
    int circularLength = ((data[tailCell+1] - data[tailCell]) % CELL_STORAGE + CELL_STORAGE) % CELL_STORAGE + 1;

    //When there's no need to start a next cell.
    if( circularLength < 27 ) {
        //Move tail forward in the queue circle.
        //This is the tricky part: 
        //  The pointers to the circular queue str is 3~30 inclusively.
        data[tailCell+1] = (data[tailCell+1]+1-3) % CELL_STORAGE + 3;
        data[tailCell+data[tailCell+1]] = b;
        //Break out the funciton.
        return;
    } 

    //If the cell is full, find a new cell.
    unsigned int newCellID = startANewCell();

    //If we run out of cells.
    if (newCellID == MAX_NQUEUES + 1) on_out_of_memory();

    //If we manage to find a new cell, enqueue new element to it.
    else {
        //Get the data position to the new cell.
        unsigned int nextCell = (newCellID-1) * CELL_SIZE + CELL_START;

        //Set both local head and tail ptr to the first storage position.
        data[nextCell] = 3;
        data[nextCell+1] = 3;

        //Put the value in it.
        data[nextCell+3] = b;

        //Link the current cell to the next cell.
        data[tailCell+2] = newCellID;

        //Update the tail ptr.
        *(q+1) = newCellID;
    }
    return;
}

//Get an element from the head of the specified queue.
//When deleting a last element from a queue, 
//  the queue is still kept alive as an empty queue.
//Exit the program when trying to dequeue an empty queue.
unsigned char dequeue_byte(Q* q){
    //Check if q is valid. Exit if not.
    QChecker(q);

    unsigned int headCell = (*q - 1) * CELL_SIZE + CELL_START;

    //Make sure the tail cell is activated. Exit otherwise.
    if(data[headCell] == 0) on_illegal_operation();

    //This only happens when trying to dequeue an empty queue. Exit.
    if(data[headCell] == 1) on_illegal_operation();
    
    //Get return value.
    unsigned int rc = data[headCell+data[headCell]];

    //If there's only one element left
    if (data[headCell] == data[headCell+1]){
        //Check if this is the last cell in the queue.
        if (*q == *(q+1)){
            //If yes, keep this cell activated.
            data[headCell] = 1;
        }
        //If there's a child cell, reset the head ptr to it
        else {
            //deactivate this cell
            data[headCell] = 0;

            //reset the head ptr
            *q = data[headCell+2];
        }     
        return rc;  
    }

    //If there's still sth in this cell, move local head ptr forward
    //This is the tricky part: 
    //  The pointers to the circular queue str are 3~30 inclusively.
    data[headCell] = (data[headCell]+1-3) % CELL_STORAGE + 3;

    return rc;   
}

//Destroy the specified queue.
void destroy_queue(Q* q){
    //Check if q is valid. Exit if not.
    QChecker(q);

    //Deactivate each cells in the queue.
    unsigned int itr = *q;
    while (true){
        //deactivate the cell.
        unsigned int currentCell = (itr - 1) * CELL_SIZE + CELL_START;
        data[currentCell] = 0;

        //If there's no proceeding cells.
        if(itr == *(q+1)) break;

        //If there's a next next cell.
        itr = data[currentCell+2];
    }

    //Deactivate the queue
    *q = 0;
}

int main(){
    //test cases copied from the instruction
    Q * q0 = create_queue(); enqueue_byte(q0, 0); enqueue_byte(q0, 1);
    Q * q1 = create_queue(); enqueue_byte(q1, 3); enqueue_byte(q0, 2); 
    enqueue_byte(q1, 4); 
    printf("%d", dequeue_byte(q0)); 
    printf("%d\n", dequeue_byte(q0)); 
    enqueue_byte(q0, 5); 
    enqueue_byte(q1, 6);
    printf("%d", dequeue_byte(q0)); 
    printf("%d\n", dequeue_byte(q0)); 
    destroy_queue(q0);
    printf("%d", dequeue_byte(q1)); 
    printf("%d", dequeue_byte(q1)); 
    printf("%d\n", dequeue_byte(q1)); 
    destroy_queue(q1);
    return 0;
}